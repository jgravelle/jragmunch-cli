import json

from jragmunch.parsers import has_server, parse_stream


def test_parse_init_and_result():
    lines = [
        json.dumps(
            {
                "type": "system",
                "subtype": "init",
                "model": "claude-opus-4-7",
                "mcp_servers": [{"name": "jcodemunch"}, {"name": "fetch"}],
            }
        ),
        json.dumps(
            {
                "type": "result",
                "result": "answer text",
                "usage": {"input_tokens": 100, "output_tokens": 42},
                "total_cost_usd": 0.0123,
                "duration_ms": 4500,
                "is_error": False,
            }
        ),
    ]
    r = parse_stream(lines)
    assert r.text == "answer text"
    assert r.tokens_in == 100
    assert r.tokens_out == 42
    assert r.cost_usd == 0.0123
    assert r.wall_time_ms == 4500
    assert r.model == "claude-opus-4-7"
    assert has_server(r, "jcodemunch")
    assert not has_server(r, "missing")
    assert r.error is None


def test_parse_handles_garbage_lines():
    lines = ["", "not json", json.dumps({"type": "result", "result": "ok"})]
    r = parse_stream(lines)
    assert r.text == "ok"


def test_parse_marks_error():
    lines = [
        json.dumps(
            {"type": "result", "result": "boom", "is_error": True, "usage": {}, "duration_ms": 0}
        )
    ]
    r = parse_stream(lines)
    assert r.error is not None
