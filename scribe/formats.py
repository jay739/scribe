"""Render transcription results to txt, srt, vtt, md and json."""

from __future__ import annotations

import json


def _ts(seconds: float, sep: str) -> str:
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _clock(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def _line(u: dict) -> str:
    prefix = f"{u['speaker']}: " if u.get("speaker") else ""
    return f"{prefix}{u['text']}"


def to_txt(result: dict) -> str:
    lines = [f"[{_clock(u['start'])}] {_line(u)}" for u in result["utterances"]]
    return "\n".join(lines) + "\n"


def to_srt(result: dict) -> str:
    blocks = []
    for i, u in enumerate(result["utterances"], start=1):
        blocks.append(
            f"{i}\n{_ts(u['start'], ',')} --> {_ts(u['end'], ',')}\n{_line(u)}\n"
        )
    return "\n".join(blocks)


def to_vtt(result: dict) -> str:
    blocks = ["WEBVTT\n"]
    for u in result["utterances"]:
        blocks.append(f"{_ts(u['start'], '.')} --> {_ts(u['end'], '.')}\n{_line(u)}\n")
    return "\n".join(blocks)


def to_md(result: dict) -> str:
    lines = [f"# Transcript: {result.get('filename', '')}\n"]
    if result.get("speakers"):
        lines.append("Speakers: " + ", ".join(result["speakers"]) + "\n")
    for u in result["utterances"]:
        who = f"**{u['speaker']}**" if u.get("speaker") else ""
        lines.append(f"`{_clock(u['start'])}` {who} {u['text']}\n")
    return "\n".join(lines)


def to_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


RENDERERS = {
    "txt": (to_txt, "text/plain"),
    "srt": (to_srt, "application/x-subrip"),
    "vtt": (to_vtt, "text/vtt"),
    "md": (to_md, "text/markdown"),
    "json": (to_json, "application/json"),
}


def render(result: dict, fmt: str) -> tuple[str, str]:
    """Return (content, mime type) for the requested format."""
    if fmt not in RENDERERS:
        raise ValueError(f"unknown format {fmt!r}, expected one of {sorted(RENDERERS)}")
    fn, mime = RENDERERS[fmt]
    return fn(result), mime
