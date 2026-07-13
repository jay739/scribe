"""Environment-driven configuration.

Importing this module is side-effectful on purpose: it loads `.env` from the
repo root and points every model cache (Hugging Face, CTranslate2) at the
configured models directory so nothing heavy lands on the system drive.
Import it before any module that touches torch, faster_whisper or pyannote.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")


def _path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    p = Path(value) if value else default
    p.mkdir(parents=True, exist_ok=True)
    return p


DATA_DIR = _path("SCRIBE_DATA_DIR", ROOT / "data")
MODELS_DIR = _path("SCRIBE_MODELS_DIR", ROOT / "models")

UPLOADS_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"
DB_PATH = DATA_DIR / "jobs.db"
UPLOADS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Keep every Hugging Face download inside MODELS_DIR.
os.environ.setdefault("HF_HOME", str(MODELS_DIR / "hf"))


def _find_hf_token() -> str | None:
    for name in ("SCRIBE_HF_TOKEN", "HF_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    # token files written by `hf auth login`, both redirected and default homes
    for candidate in (
        Path(os.environ["HF_HOME"]) / "token",
        Path.home() / ".cache" / "huggingface" / "token",
    ):
        if candidate.exists():
            token = candidate.read_text(encoding="utf-8").strip()
            if token:
                return token
    return None


MODEL = os.environ.get("SCRIBE_MODEL", "large-v3")
DEVICE = os.environ.get("SCRIBE_DEVICE", "cuda")
COMPUTE = os.environ.get("SCRIBE_COMPUTE", "int8_float16")
HF_TOKEN = _find_hf_token()
PORT = int(os.environ.get("SCRIBE_PORT", "8323"))
HOST = os.environ.get("SCRIBE_HOST", "127.0.0.1")

DIARIZATION_MODEL = os.environ.get(
    "SCRIBE_DIARIZATION_MODEL", "pyannote/speaker-diarization-community-1"
)
