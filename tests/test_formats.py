import json

import pytest

from scribe.formats import render

RESULT = {
    "id": "abc",
    "filename": "meeting.mp3",
    "duration": 12.5,
    "language": "en",
    "language_probability": 0.99,
    "model": "large-v3",
    "diarization": {"requested": True, "applied": True, "note": None},
    "speakers": ["Speaker 1", "Speaker 2"],
    "utterances": [
        {"start": 0.0, "end": 2.5, "speaker": "Speaker 1", "text": "Hello there."},
        {"start": 3.0, "end": 5.25, "speaker": "Speaker 2", "text": "Hi, how are you?"},
    ],
    "segments": [],
}


def test_txt():
    content, mime = render(RESULT, "txt")
    assert mime == "text/plain"
    assert "[0:00] Speaker 1: Hello there." in content
    assert "[0:03] Speaker 2: Hi, how are you?" in content


def test_srt_timestamps_and_numbering():
    content, _ = render(RESULT, "srt")
    blocks = content.strip().split("\n\n")
    assert blocks[0].splitlines() == [
        "1",
        "00:00:00,000 --> 00:00:02,500",
        "Speaker 1: Hello there.",
    ]
    assert blocks[1].splitlines()[0] == "2"
    assert "00:00:03,000 --> 00:00:05,250" in blocks[1]


def test_vtt_header_and_dot_millis():
    content, mime = render(RESULT, "vtt")
    assert mime == "text/vtt"
    assert content.startswith("WEBVTT")
    assert "00:00:02.500" in content


def test_json_roundtrip():
    content, mime = render(RESULT, "json")
    assert mime == "application/json"
    assert json.loads(content)["speakers"] == ["Speaker 1", "Speaker 2"]


def test_md_speaker_bold():
    content, _ = render(RESULT, "md")
    assert "**Speaker 1**" in content


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        render(RESULT, "docx")


def test_no_speaker_lines_have_no_prefix():
    plain = dict(RESULT)
    plain["utterances"] = [
        {"start": 0.0, "end": 1.0, "speaker": None, "text": "Just text."}
    ]
    content, _ = render(plain, "txt")
    assert "None" not in content
    assert "[0:00] Just text." in content
