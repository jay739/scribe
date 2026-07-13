"""Make CUDA runtime DLLs visible to CTranslate2 on Windows.

The PyTorch CUDA wheels bundle every DLL faster-whisper needs (cuBLAS,
cuDNN 9), but Windows does not search another package's directory when
ctranslate2.dll resolves its imports. Registering torch's lib directory,
plus any nvidia-* pip packages if present, fixes that without a system-wide
CUDA Toolkit install. Call setup() before importing faster_whisper.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def setup() -> None:
    if sys.platform != "win32":
        return

    candidates: list[Path] = []

    try:
        import torch

        candidates.append(Path(torch.__file__).parent / "lib")
    except ImportError:
        pass

    # nvidia-cublas-cu12 / nvidia-cudnn-cu12 style pip packages, if installed
    for base in map(Path, sys.path):
        nvidia = base / "nvidia"
        if nvidia.is_dir():
            candidates.extend(nvidia.glob("*/bin"))

    for path in candidates:
        if path.is_dir():
            os.add_dll_directory(str(path))
            os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")
