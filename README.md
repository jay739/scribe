# scribe

Self-hosted, GPU-accelerated transcription with speaker labels. An open-source alternative to Otter.ai that runs entirely on your own hardware.

No cloud, no accounts, no per-minute billing. Your audio never leaves the machine.

## Features

| Feature             | Detail                                                                                                                                         |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Transcription       | Whisper large-v3 via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2, CUDA, int8_float16)                             |
| Speaker diarization | [pyannote.audio](https://github.com/pyannote/pyannote-audio), optional; without it scribe still transcribes and reports why labels are missing |
| Web UI              | Drag and drop a file, watch progress, read a color-coded transcript                                                                            |
| API                 | Upload, poll, fetch results as JSON                                                                                                            |
| CLI                 | `scribe transcribe meeting.mp3 --diarize -f srt`                                                                                               |
| Exports             | TXT, SRT, VTT, JSON, Markdown                                                                                                                  |

## Requirements

- NVIDIA GPU with CUDA support (tested on an RTX 3060 Ti, 8 GB VRAM). CPU works but is slow.
- Windows or Linux, Python 3.12 (the setup script installs its own via [uv](https://github.com/astral-sh/uv))
- Roughly 6 GB of disk for models on first run

## Install

### Quick start (Windows)

```powershell
git clone https://github.com/jay739/scribe && cd scribe
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
.venv\Scripts\python -m scribe.server
```

Then open http://localhost:8323.

### Speaker diarization setup

Diarization uses a gated Hugging Face model, so it needs a one-time token setup:

1. Create a free token at https://huggingface.co/settings/tokens
2. Accept the conditions at https://huggingface.co/pyannote/speaker-diarization-community-1
3. Put the token in `.env` at the repo root: `SCRIBE_HF_TOKEN=hf_...`

Without a token scribe still transcribes, it just cannot tell speakers apart.

## Usage

### CLI

```powershell
.venv\Scripts\python -m scribe.cli transcribe path\to\audio.mp3 --diarize -f srt -o out\
```

### Web UI and API

Run the server (`python -m scribe.server`) and open http://localhost:8323 for the drag-and-drop UI, or drive it programmatically: upload a file, poll the job, then fetch the result in any export format.

## Configuration

Every setting is an environment variable, or a line in `.env` at the repo root:

| Variable                   | Default                                    | Meaning                                                                                                   |
| -------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| `SCRIBE_MODEL`             | `large-v3`                                 | Whisper model size (`tiny` ... `large-v3`)                                                                |
| `SCRIBE_DEVICE`            | `cuda`                                     | `cuda` or `cpu`                                                                                           |
| `SCRIBE_COMPUTE`           | `int8_float16`                             | CTranslate2 compute type                                                                                  |
| `SCRIBE_HF_TOKEN`          | unset                                      | Hugging Face token for diarization (falls back to `HF_TOKEN`, then the standard Hugging Face token cache) |
| `SCRIBE_DIARIZATION_MODEL` | `pyannote/speaker-diarization-community-1` | Diarization pipeline to load                                                                              |
| `SCRIBE_HOST`              | `127.0.0.1`                                | Server bind address; set `0.0.0.0` to expose on the network                                               |
| `SCRIBE_PORT`              | `8323`                                     | Server port                                                                                               |
| `SCRIBE_DATA_DIR`          | `./data`                                   | Uploads, results, job database                                                                            |
| `SCRIBE_MODELS_DIR`        | `./models`                                 | Model cache (`HF_HOME` points here)                                                                       |

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and checks. Report vulnerabilities privately per [SECURITY.md](SECURITY.md).

## License

MIT, see [LICENSE](LICENSE).
