"""Command line interface.

scribe transcribe meeting.mp3 --diarize -f srt -f txt -o out/
scribe serve
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import audio, config, formats
from .engine import diarizer, merge, transcriber


def _cmd_transcribe(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"error: {src} does not exist", file=sys.stderr)
        return 2

    out_dir = Path(args.output) if args.output else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    fmts = args.format or ["txt"]

    t0 = time.time()
    print(f"decoding {src.name} ...")
    samples = audio.decode(src)
    duration = audio.duration_seconds(samples)
    print(f"  {duration:.1f}s of audio")

    print(f"transcribing with {args.model or config.MODEL} on {config.DEVICE} ...")

    def on_progress(frac: float) -> None:
        print(f"\r  {frac * 100:5.1f}%", end="", flush=True)

    tx = transcriber.transcribe(
        samples,
        language=args.language,
        model_size=args.model,
        on_progress=on_progress,
    )
    print(f"\r  100.0%  (language: {tx['language']})")

    turns: list[dict] = []
    note = None
    if args.diarize:
        print("diarizing ...")
        try:
            turns = diarizer.diarize(samples)
            n = len({t["speaker"] for t in turns})
            print(f"  {n} speaker(s) found")
        except diarizer.DiarizationUnavailable as exc:
            note = str(exc)
            print(f"  diarization skipped: {note}", file=sys.stderr)

    utterances = merge.merge(tx["segments"], turns)
    result = {
        "id": src.stem,
        "filename": src.name,
        "duration": round(duration, 3),
        "language": tx["language"],
        "language_probability": tx["language_probability"],
        "model": args.model or config.MODEL,
        "diarization": {
            "requested": args.diarize,
            "applied": bool(turns),
            "note": note,
        },
        "speakers": merge.speakers(utterances),
        "utterances": utterances,
        "segments": tx["segments"],
    }

    for fmt in fmts:
        content, _ = formats.render(result, fmt)
        dest = out_dir / f"{src.stem}.{fmt}"
        dest.write_text(content, encoding="utf-8")
        print(f"wrote {dest}")

    print(f"done in {time.time() - t0:.1f}s")
    return 0


def _cmd_serve(_args: argparse.Namespace) -> int:
    from . import server

    server.main()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scribe", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    tr = sub.add_parser("transcribe", help="transcribe an audio or video file")
    tr.add_argument("file", help="path to the input file")
    tr.add_argument("--diarize", action="store_true", help="label speakers")
    tr.add_argument("--language", help="force a language code, e.g. en")
    tr.add_argument("--model", help=f"whisper model size (default {config.MODEL})")
    tr.add_argument(
        "-f",
        "--format",
        action="append",
        choices=sorted(formats.RENDERERS),
        help="output format, repeatable (default txt)",
    )
    tr.add_argument("-o", "--output", help="output directory (default: next to input)")
    tr.set_defaults(fn=_cmd_transcribe)

    sv = sub.add_parser("serve", help="run the web UI and API server")
    sv.set_defaults(fn=_cmd_serve)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
