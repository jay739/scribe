# Build report: scribe

Autonomous build completed 2026-07-13 on the RTX 3060 Ti box. Working tree: `D:\projects\scribe`.

## What was built

A complete self-hosted transcription service, per MISSION.md:

- **Engine**: PyAV decode to 16 kHz mono, faster-whisper 1.2.1 (`large-v3`, `int8_float16`) on CUDA, pyannote.audio 4.0.7 diarization, word-level speaker merge, five export formats (txt, srt, vtt, md, json).
- **Service**: FastAPI server on port 8323 with upload, job list, status, result, export and delete endpoints. SQLite-backed queue with a single GPU worker thread, jobs survive restarts.
- **Web UI**: single static page, drag and drop, live progress polling, color-coded speaker transcript, export buttons, dark and light theme.
- **CLI**: `python -m scribe.cli transcribe file --diarize -f srt -o out/`.
- **Environment**: Python 3.12 venv via uv, torch 2.11.0+cu128. Everything (venv, uv cache, model cache, runtime data) lives inside the repo on D:, nothing on C:.

## Verified end to end

- 13 unit tests pass (merge logic, export formats).
- CUDA sanity: torch sees the 3060 Ti, CTranslate2 reports 1 CUDA device through the `cuda_dlls.py` shim, so no system CUDA Toolkit install was needed.
- Synthetic two-speaker dialogue (46.9 s, generated with Windows SAPI voices by `scripts/make_test_audio.ps1`) transcribed **word-perfect** by the CLI in 62.8 s including first model load. Later runs with the model warm are much faster.
- Same file through the HTTP API: upload accepted, job queued, progressed through stages, result JSON correct (8 utterances, language en), SRT and VTT exports well-formed, UI and static assets serve, delete removes the job plus its files on disk.
- Graceful degradation confirmed: with no Hugging Face token, both CLI and server complete transcription and report exactly why speaker labels are missing.

## Known limitations

1. **Diarization is not yet live-tested.** The merge logic is unit-tested and the pipeline code follows the pyannote 4.x API, but the gated model needs a one-time manual step: create a token at https://huggingface.co/settings/tokens, accept the conditions at https://huggingface.co/pyannote/speaker-diarization-community-1, put `SCRIBE_HF_TOKEN=hf_...` in `.env`, then re-run the sample and confirm two speakers come back.
2. Whisper hallucinated nothing on the clean TTS sample, but real-world noisy audio will benefit from tuning (VAD parameters are currently defaults).
3. Single worker by design. Fine for one user, revisit if it ever serves the whole homelab.

## Deferred (intentionally)

- GitHub push (`jay739/scribe`), Discussions, icons and landing page per the usual project conventions.
- Docker image with CPU fallback for batcave deployment behind nginx.
- Live microphone streaming, folder watch, Jellyfin subtitle integration.

## How to run

```powershell
cd D:\projects\scribe
.venv\Scripts\python.exe -m scribe.server    # web UI on http://localhost:8323
.venv\Scripts\python.exe -m scribe.cli transcribe path\to\file.mp3 --diarize -f srt
```
