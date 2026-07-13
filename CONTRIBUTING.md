# Contributing to scribe

Thanks for taking an interest. This project is young and small on purpose, so contributing is simple.

## Getting set up

```powershell
git clone https://github.com/jay739/scribe && cd scribe
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

On Linux or macOS, create a Python 3.12 venv, install torch for your platform, then `pip install -e ".[dev]"`.

## Running tests

```
.venv\Scripts\python.exe -m pytest
```

The test suite covers the pure-Python parts (speaker merging, export formats) and runs in well under a second. GPU-dependent code paths are exercised manually: generate a sample with `scripts/make_test_audio.ps1` and run the CLI against it.

## Ground rules

- Keep the engine modules (`scribe/engine/`) importable without a GPU. Heavy imports happen lazily inside functions.
- Nothing outside `data/` and `models/` may be written to at runtime.
- New export formats go in `scribe/formats.py` with a test in `tests/test_formats.py`.
- One feature per pull request, and please describe the behavior change, not just the code change.

## Reporting bugs

Open a GitHub issue with the command or request you ran, what you expected, and what happened instead. For transcription quality issues, attach a short audio clip when possible.
