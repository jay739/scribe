"""Decode any audio or video file to 16 kHz mono float32 PCM.

Uses PyAV (bundled FFmpeg, already a faster-whisper dependency) so there is
no system ffmpeg requirement. Both the transcriber and the diarizer consume
the same decoded array, so every input is decoded exactly once.
"""

from __future__ import annotations

from pathlib import Path

import av
import numpy as np

SAMPLE_RATE = 16000


def decode(path: str | Path) -> np.ndarray:
    """Return mono float32 samples in [-1, 1] at 16 kHz."""
    chunks: list[np.ndarray] = []
    with av.open(str(path)) as container:
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                chunks.append(np.frombuffer(bytes(resampled.planes[0]), dtype=np.int16))
        # flush the resampler
        for resampled in resampler.resample(None):
            chunks.append(np.frombuffer(bytes(resampled.planes[0]), dtype=np.int16))

    if not chunks:
        raise ValueError(f"no audio decoded from {path}")

    pcm = np.concatenate(chunks).astype(np.float32) / 32768.0
    return pcm


def duration_seconds(samples: np.ndarray) -> float:
    return len(samples) / SAMPLE_RATE
