from scribe.engine.merge import merge, relabel, speakers


def seg(start, end, text, words=None):
    return {"start": start, "end": end, "text": text, "words": words or []}


def word(start, end, w):
    return {"start": start, "end": end, "word": w, "probability": 0.9}


def test_no_turns_passthrough():
    segments = [seg(0.0, 1.0, "hello"), seg(1.2, 2.0, "world")]
    utts = merge(segments, [])
    assert len(utts) == 2
    assert utts[0]["speaker"] is None
    assert utts[0]["text"] == "hello"


def test_segment_level_assignment():
    segments = [seg(0.0, 1.0, "hi there"), seg(2.0, 3.0, "hello back")]
    turns = [
        {"start": 0.0, "end": 1.5, "speaker": "SPEAKER_00"},
        {"start": 1.5, "end": 3.5, "speaker": "SPEAKER_01"},
    ]
    utts = merge(segments, turns)
    assert [u["speaker"] for u in utts] == ["Speaker 1", "Speaker 2"]


def test_word_level_split_mid_segment():
    words = [
        word(0.0, 0.4, " one"),
        word(0.4, 0.9, " two"),
        word(2.1, 2.5, " three"),
        word(2.5, 3.0, " four"),
    ]
    segments = [seg(0.0, 3.0, "one two three four", words)]
    turns = [
        {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
        {"start": 2.0, "end": 3.2, "speaker": "SPEAKER_01"},
    ]
    utts = merge(segments, turns)
    assert len(utts) == 2
    assert utts[0]["text"] == "one two"
    assert utts[0]["speaker"] == "Speaker 1"
    assert utts[1]["text"] == "three four"
    assert utts[1]["speaker"] == "Speaker 2"


def test_adjacent_same_speaker_merged():
    segments = [
        seg(0.0, 1.0, "first bit", [word(0.0, 1.0, " first bit")]),
        seg(1.2, 2.0, "second bit", [word(1.2, 2.0, " second bit")]),
    ]
    turns = [{"start": 0.0, "end": 2.5, "speaker": "SPEAKER_00"}]
    utts = merge(segments, turns)
    assert len(utts) == 1
    assert utts[0]["text"] == "first bit second bit"
    assert utts[0]["end"] == 2.0


def test_no_overlap_falls_back_to_nearest():
    segments = [seg(5.0, 6.0, "late words", [word(5.0, 6.0, " late words")])]
    turns = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"}]
    utts = merge(segments, turns)
    assert utts[0]["speaker"] == "Speaker 1"


def test_relabel_order_of_appearance():
    utts = [
        {"start": 0, "end": 1, "speaker": "SPEAKER_07", "text": "a"},
        {"start": 1, "end": 2, "speaker": "SPEAKER_02", "text": "b"},
        {"start": 2, "end": 3, "speaker": "SPEAKER_07", "text": "c"},
    ]
    relabel(utts)
    assert [u["speaker"] for u in utts] == ["Speaker 1", "Speaker 2", "Speaker 1"]
    assert speakers(utts) == ["Speaker 1", "Speaker 2"]
