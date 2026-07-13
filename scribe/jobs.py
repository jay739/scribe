"""SQLite-backed job store with a single GPU worker thread.

One worker on purpose: the GPU serializes heavy jobs anyway, and a queue of
one avoids VRAM contention between Whisper and pyannote. Jobs survive
restarts; anything left queued or running is re-enqueued on startup.
"""

from __future__ import annotations

import json
import queue
import sqlite3
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Optional

from . import audio, config, formats
from .engine import diarizer, merge, transcriber

_conn: sqlite3.Connection | None = None
_db_lock = threading.Lock()
_queue: "queue.Queue[str]" = queue.Queue()
_worker: threading.Thread | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    upload_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    stage TEXT,
    progress REAL NOT NULL DEFAULT 0,
    error TEXT,
    options TEXT NOT NULL DEFAULT '{}',
    warning TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute(_SCHEMA)
        _conn.commit()
    return _conn


def _update(job_id: str, **fields) -> None:
    fields["updated_at"] = time.time()
    cols = ", ".join(f"{k} = ?" for k in fields)
    with _db_lock:
        _db().execute(
            f"UPDATE jobs SET {cols} WHERE id = ?", [*fields.values(), job_id]
        )
        _db().commit()


def create(filename: str, upload_path: Path, options: dict) -> str:
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    with _db_lock:
        _db().execute(
            "INSERT INTO jobs (id, filename, upload_path, options, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, filename, str(upload_path), json.dumps(options), now, now),
        )
        _db().commit()
    _queue.put(job_id)
    return job_id


def get(job_id: str) -> Optional[dict]:
    with _db_lock:
        row = _db().execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_jobs(limit: int = 50) -> list[dict]:
    with _db_lock:
        rows = (
            _db()
            .execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
            .fetchall()
        )
    return [_row_to_dict(r) for r in rows]


def delete(job_id: str) -> bool:
    job = get(job_id)
    if job is None:
        return False
    with _db_lock:
        _db().execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        _db().commit()
    for path in (Path(job["upload_path"]), result_path(job_id)):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return True


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["options"] = json.loads(d["options"] or "{}")
    return d


def result_path(job_id: str) -> Path:
    return config.RESULTS_DIR / f"{job_id}.json"


def load_result(job_id: str) -> Optional[dict]:
    path = result_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _run_job(job_id: str) -> None:
    job = get(job_id)
    if job is None:
        return
    options = job["options"]
    want_diarize = bool(options.get("diarize", True))
    language = options.get("language") or None
    model_size = options.get("model") or None
    warning = None

    # stage weights for a single progress number
    transcribe_share = 0.55 if want_diarize else 0.9

    try:
        _update(job_id, status="running", stage="decode", progress=0.02)
        samples = audio.decode(job["upload_path"])
        duration = audio.duration_seconds(samples)

        _update(job_id, stage="transcribe", progress=0.05)

        def on_progress(frac: float) -> None:
            _update(job_id, progress=0.05 + frac * transcribe_share)

        tx = transcriber.transcribe(
            samples,
            language=language,
            model_size=model_size,
            on_progress=on_progress,
        )

        turns: list[dict] = []
        if want_diarize:
            _update(job_id, stage="diarize", progress=0.05 + transcribe_share)
            try:
                turns = diarizer.diarize(samples)
            except diarizer.DiarizationUnavailable as exc:
                warning = str(exc)

        _update(job_id, stage="merge", progress=0.95)
        utterances = merge.merge(tx["segments"], turns)

        result = {
            "id": job_id,
            "filename": job["filename"],
            "duration": round(duration, 3),
            "language": tx["language"],
            "language_probability": tx["language_probability"],
            "model": model_size or config.MODEL,
            "diarization": {
                "requested": want_diarize,
                "applied": bool(turns),
                "note": warning,
            },
            "speakers": merge.speakers(utterances),
            "utterances": utterances,
            "segments": tx["segments"],
        }
        result_path(job_id).write_text(formats.to_json(result), encoding="utf-8")
        _update(job_id, status="done", stage=None, progress=1.0, warning=warning)
    except Exception as exc:  # noqa: BLE001 - job errors must not kill the worker
        _update(
            job_id,
            status="error",
            error=f"{exc}\n{traceback.format_exc(limit=5)}",
        )


def _worker_loop() -> None:
    while True:
        job_id = _queue.get()
        try:
            _run_job(job_id)
        finally:
            _queue.task_done()


def start_worker() -> None:
    """Start the worker thread and re-enqueue unfinished jobs."""
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    with _db_lock:
        rows = (
            _db()
            .execute(
                "SELECT id FROM jobs WHERE status IN ('queued', 'running')"
                " ORDER BY created_at"
            )
            .fetchall()
        )
    for row in rows:
        _update(row["id"], status="queued", stage=None, progress=0)
        _queue.put(row["id"])
    _worker = threading.Thread(target=_worker_loop, name="scribe-worker", daemon=True)
    _worker.start()
