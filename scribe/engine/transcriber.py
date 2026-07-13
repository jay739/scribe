"""faster-whisper wrapper with lazy model loading and progress reporting."""

from __future__ import annotations

import threading
from typing import Callable, Optional

import numpy as np

from .. import config, cuda_dlls

_lock = threading.Lock()
_model = None
_model_key: tuple[str, str, str] | None = None

ProgressFn = Callable[[float], None]


def _get_model(model_size: str, device: str, compute: str):
    global _model, _model_key
    with _lock:
        key = (model_size, device, compute)
        if _model is None or _model_key != key:
            cuda_dlls.setup()
            from faster_whisper import WhisperModel

            _model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute,
                download_root=str(config.MODELS_DIR / "whisper"),
            )
            _model_key = key
        return _model


def release() -> None:
    """Drop the loaded model to free VRAM."""
    global _model, _model_key
    with _lock:
        _model = None
        _model_key = None


def transcribe(
    samples: np.ndarray,
    *,
    language: Optional[str] = None,
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute: Optional[str] = None,
    word_timestamps: bool = True,
    on_progress: Optional[ProgressFn] = None,
) -> dict:
    """Transcribe 16 kHz mono float32 samples. Returns a plain-dict result."""
    model = _get_model(
        model_size or config.MODEL,
        device or config.DEVICE,
        compute or config.COMPUTE,
    )

    duration = len(samples) / 16000.0
    segments_iter, info = model.transcribe(
        samples,
        language=language,
        vad_filter=True,
        word_timestamps=word_timestamps,
        beam_size=5,
    )

    segments = []
    for seg in segments_iter:
        words = [
            {
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "word": w.word,
                "probability": round(w.probability, 3),
            }
            for w in (seg.words or [])
        ]
        segments.append(
            {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": words,
            }
        )
        if on_progress and duration > 0:
            on_progress(min(seg.end / duration, 1.0))

    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(duration, 3),
        "segments": segments,
    }
