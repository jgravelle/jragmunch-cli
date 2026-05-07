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


def test_assistant_text_accumulates_when_result_is_empty():
    """Regression: turn ends in a tool_use block, so the terminal `result` event
    has `result == ""`. Previously parse_stream dropped the model's findings on
    the floor despite usage.output_tokens being non-zero. The accumulator must
    reconstruct the text from the assistant message content blocks.
    """
    lines = [
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "## Findings\n\n"},
                        {"type": "text", "text": "- 1.1 [high] foo\n"},
                    ]
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "mcp__jcodemunch__get_symbol_source"},
                    ]
                },
            }
        ),
        json.dumps(
            {
                "type": "result",
                "result": "",
                "usage": {"input_tokens": 13, "output_tokens": 10321},
                "total_cost_usd": 1.22,
                "duration_ms": 398454,
            }
        ),
    ]
    r = parse_stream(lines)
    assert r.text == "## Findings\n\n- 1.1 [high] foo\n"
    assert r.tokens_out == 10321
    assert r.cost_usd == 1.22


def test_result_text_wins_when_populated():
    """Clean text-only turns should still resolve to the terminal result event's
    `result` field — the canonical answer. The accumulator only fills in when
    the result event is empty.
    """
    lines = [
        json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "draft"}]},
            }
        ),
        json.dumps(
            {
                "type": "result",
                "result": "final canonical answer",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "duration_ms": 100,
            }
        ),
    ]
    r = parse_stream(lines)
    assert r.text == "final canonical answer"
