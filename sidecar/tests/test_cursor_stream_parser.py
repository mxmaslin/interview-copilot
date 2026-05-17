from __future__ import annotations

from copilot.cursor_stream import parse_answer_stream_line


def test_parse_delta() -> None:
    kind, obj = parse_answer_stream_line('{"event":"delta","text":"При"}')
    assert kind == "delta"
    assert obj is not None
    assert obj["text"] == "При"


def test_parse_done() -> None:
    kind, obj = parse_answer_stream_line(
        '{"event":"done","status":"finished","text":"Полный ответ","runId":"r1"}'
    )
    assert kind == "done"
    assert obj is not None
    assert obj["text"] == "Полный ответ"


def test_parse_legacy_final() -> None:
    kind, obj = parse_answer_stream_line(
        '{"status":"finished","text":"legacy","runId":"x"}'
    )
    assert kind == "done"
    assert obj is not None


def test_parse_skip() -> None:
    assert parse_answer_stream_line("not json") == ("skip", None)
