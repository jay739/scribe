"""Merge Whisper segments with diarization turns into speaker utterances.

Pure Python, no torch imports, unit-testable. Words are assigned to the
diarization turn with the largest temporal overlap (nearest turn when there
is no overlap at all), then consecutive words with the same speaker are
grouped into utterances. Speakers are renamed in order of first appearance.
"""

from __future__ import annotations


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _speaker_for_span(start: float, end: float, turns: list[dict]) -> str | None:
    if not turns:
        return None
    best, best_overlap = None, 0.0
    for t in turns:
        ov = _overlap(start, end, t["start"], t["end"])
        if ov > best_overlap:
            best, best_overlap = t["speaker"], ov
    if best is not None:
        return best
    # no overlap anywhere: fall back to the turn whose midpoint is nearest
    mid = (start + end) / 2
    nearest = min(turns, key=lambda t: abs((t["start"] + t["end"]) / 2 - mid))
    return nearest["speaker"]


def merge(segments: list[dict], turns: list[dict]) -> list[dict]:
    """Build utterances: [{"start", "end", "speaker", "text"}, ...]

    With no turns (diarization off), each Whisper segment becomes one
    utterance with speaker None.
    """
    if not turns:
        return [
            {
                "start": s["start"],
                "end": s["end"],
                "speaker": None,
                "text": s["text"],
            }
            for s in segments
        ]

    # word-level assignment when word timestamps exist, else segment-level
    utterances: list[dict] = []

    def push(start: float, end: float, speaker: str | None, text: str) -> None:
        text = text.strip()
        if not text:
            return
        prev = utterances[-1] if utterances else None
        if (
            prev is not None
            and prev["speaker"] == speaker
            and start - prev["end"] < 1.0
        ):
            prev["end"] = end
            prev["text"] = f"{prev['text']} {text}"
        else:
            utterances.append(
                {"start": start, "end": end, "speaker": speaker, "text": text}
            )

    for seg in segments:
        words = seg.get("words") or []
        if not words:
            speaker = _speaker_for_span(seg["start"], seg["end"], turns)
            push(seg["start"], seg["end"], speaker, seg["text"])
            continue

        run_words: list[dict] = []
        run_speaker: str | None = None
        for w in words:
            speaker = _speaker_for_span(w["start"], w["end"], turns)
            if run_words and speaker != run_speaker:
                push(
                    run_words[0]["start"],
                    run_words[-1]["end"],
                    run_speaker,
                    "".join(x["word"] for x in run_words),
                )
                run_words = []
            run_words.append(w)
            run_speaker = speaker
        if run_words:
            push(
                run_words[0]["start"],
                run_words[-1]["end"],
                run_speaker,
                "".join(x["word"] for x in run_words),
            )

    return relabel(utterances)


def relabel(utterances: list[dict]) -> list[dict]:
    """Rename raw diarization labels to 'Speaker 1', 'Speaker 2', ... by
    order of first appearance."""
    mapping: dict[str, str] = {}
    for u in utterances:
        raw = u["speaker"]
        if raw is None:
            continue
        if raw not in mapping:
            mapping[raw] = f"Speaker {len(mapping) + 1}"
        u["speaker"] = mapping[raw]
    return utterances


def speakers(utterances: list[dict]) -> list[str]:
    seen: list[str] = []
    for u in utterances:
        s = u["speaker"]
        if s is not None and s not in seen:
            seen.append(s)
    return seen
