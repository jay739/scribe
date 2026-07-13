# Mission: scribe

Self-hosted, GPU-accelerated transcription service. An open-source alternative to Otter.ai that runs entirely on local hardware.

## Goal

A single service that takes audio or video files and produces speaker-labeled, timestamped transcripts, usable three ways: a drag-and-drop web UI, a JSON API, and a CLI. Everything runs locally on the RTX 3060 Ti (CUDA), no cloud calls, no accounts, no per-minute pricing.

## Core decisions

- **ASR**: faster-whisper (CTranslate2 backend) with `large-v3`, `int8_float16` compute on CUDA. Model size is configurable via env, default large-v3.
- **Diarization**: pyannote.audio speaker-diarization pipeline on CUDA. Optional at runtime: if the model is unavailable (no HF token or terms not accepted) the service degrades gracefully to plain transcription and says so.
- **Merge**: word-level speaker assignment by timestamp overlap, re-chunked into speaker turns.
- **Server**: FastAPI + uvicorn, single background worker thread so GPU jobs serialize. SQLite job store so jobs survive restarts.
- **UI**: single static page (vanilla JS), upload, job list, transcript viewer with per-speaker colors, export TXT / SRT / VTT / JSON.
- **Python**: 3.12 in a uv-managed venv inside the repo. All caches (uv, Hugging Face models) live on D:, never C:.

## Milestones

1. **Scaffold**: repo, license, config, docs, environment bootstrap script.
2. **Engine**: audio decode, transcriber, diarizer, merge, export formats. Unit tests for the pure-Python parts.
3. **Service**: job queue, FastAPI API, web UI, CLI.
4. **Verified end-to-end**: synthetic two-speaker test clip transcribed and diarized on CUDA, outputs checked.
5. **Report**: REPORT.md with what works, what is deferred, and how to run it.

## Constraints

- 8 GB VRAM budget shared with other workloads: models load lazily and can be released.
- Disk on C: is tight, so nothing heavy is written there.
- No third-party runtime services. Hugging Face is contacted once per model download, then cached.

## Out of scope (for now)

- Live microphone / streaming transcription.
- Multi-user auth. This is a LAN/Tailscale service behind nginx like the rest of the homelab.
- Docker image (planned later for batcave deployment with CPU fallback).
