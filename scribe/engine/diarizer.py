"""pyannote.audio speaker diarization with graceful degradation.

Diarization needs a Hugging Face token that has accepted the gated model
conditions. When that is missing or the model cannot load, callers get a
DiarizationUnavailable whose message explains what to do, and the job
continues as plain transcription.
"""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np

from .. import config


class DiarizationUnavailable(RuntimeError):
    pass


_lock = threading.Lock()
_pipeline = None
_load_error: Optional[str] = None


def availability() -> tuple[bool, Optional[str]]:
    """(available, reason-if-not) without forcing a model download."""
    if _pipeline is not None:
        return True, None
    if _load_error is not None:
        return False, _load_error
    if not config.HF_TOKEN:
        return False, (
            "No Hugging Face token found. Create one at "
            "https://huggingface.co/settings/tokens, accept the conditions at "
            f"https://huggingface.co/{config.DIARIZATION_MODEL}, and set "
            "SCRIBE_HF_TOKEN in .env."
        )
    return True, None


def _get_pipeline():
    global _pipeline, _load_error
    with _lock:
        if _pipeline is not None:
            return _pipeline
        ok, reason = availability()
        if not ok:
            raise DiarizationUnavailable(reason)
        try:
            import torch
            from pyannote.audio import Pipeline

            try:
                # pyannote.audio >= 4
                pipeline = Pipeline.from_pretrained(
                    config.DIARIZATION_MODEL, token=config.HF_TOKEN
                )
            except TypeError:
                # pyannote.audio 3.x used a different keyword
                pipeline = Pipeline.from_pretrained(
                    config.DIARIZATION_MODEL, use_auth_token=config.HF_TOKEN
                )
            if pipeline is None:
                raise RuntimeError(
                    f"Pipeline.from_pretrained returned None for "
                    f"{config.DIARIZATION_MODEL}. The token probably has not "
                    "accepted the model's gated conditions."
                )
            if config.DEVICE == "cuda" and torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
            _pipeline = pipeline
            return _pipeline
        except DiarizationUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - degrade, do not crash jobs
            _load_error = f"diarization model failed to load: {exc}"
            raise DiarizationUnavailable(_load_error) from exc


def release() -> None:
    global _pipeline
    with _lock:
        _pipeline = None


def diarize(samples: np.ndarray) -> list[dict]:
    """Run diarization on 16 kHz mono float32 samples.

    Returns turns: [{"start": s, "end": e, "speaker": "SPEAKER_00"}, ...]
    """
    pipeline = _get_pipeline()

    import torch

    waveform = torch.from_numpy(samples).unsqueeze(0)
    annotation = pipeline({"waveform": waveform, "sample_rate": 16000})

    turns = [
        {"start": round(turn.start, 3), "end": round(turn.end, 3), "speaker": label}
        for turn, _, label in annotation.itertracks(yield_label=True)
    ]
    turns.sort(key=lambda t: t["start"])
    return turns
