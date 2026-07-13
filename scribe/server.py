"""FastAPI application: upload, job status, results, exports, static UI."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__, config, formats, jobs
from .engine import diarizer

WEB_DIR = Path(__file__).parent / "web"

ALLOWED_SUFFIXES = {
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".ogg",
    ".opus",
    ".aac",
    ".wma",
    ".mp4",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
}

app = FastAPI(title="scribe", version=__version__)


@app.on_event("startup")
def _startup() -> None:
    jobs.start_worker()


@app.get("/api/health")
def health() -> dict:
    diar_ok, diar_reason = diarizer.availability()
    return {
        "version": __version__,
        "model": config.MODEL,
        "device": config.DEVICE,
        "compute": config.COMPUTE,
        "diarization_available": diar_ok,
        "diarization_note": diar_reason,
    }


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    diarize: bool = Form(True),
    language: Optional[str] = Form(None),
) -> dict:
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            400,
            f"unsupported file type {suffix!r}. Allowed: {sorted(ALLOWED_SUFFIXES)}",
        )
    # reserve an id-stable path, then stream the upload to disk
    tmp_name = f"incoming-{file.filename}"
    job_id = None
    try:
        upload_path = config.UPLOADS_DIR / tmp_name
        with upload_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        job_id = jobs.create(
            filename=file.filename or "upload",
            upload_path=upload_path,
            options={"diarize": diarize, "language": language},
        )
        final_path = config.UPLOADS_DIR / f"{job_id}{suffix}"
        upload_path.rename(final_path)
        jobs._update(job_id, upload_path=str(final_path))
        return {"id": job_id}
    finally:
        await file.close()


@app.get("/api/jobs")
def list_jobs() -> list[dict]:
    return jobs.list_jobs()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    return job


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict:
    if not jobs.delete(job_id):
        raise HTTPException(404, "no such job")
    return {"deleted": job_id}


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str) -> dict:
    result = jobs.load_result(job_id)
    if result is None:
        raise HTTPException(404, "result not ready")
    return result


@app.get("/api/jobs/{job_id}/export")
def export(job_id: str, format: str = "txt") -> Response:
    result = jobs.load_result(job_id)
    if result is None:
        raise HTTPException(404, "result not ready")
    try:
        content, mime = formats.render(result, format)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    stem = Path(result.get("filename") or job_id).stem
    return Response(
        content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{stem}.{format}"'},
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
