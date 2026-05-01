import json

from jragmunch import runtime


def test_mcp_inline_default_only_jcodemunch():
    runtime.set_state(print_command=False, with_docs=False, with_data=False)
    cfg = json.loads(runtime.mcp_inline())
    assert set(cfg["mcpServers"].keys()) == {"jcodemunch"}


def test_mcp_inline_with_docs_and_data():
    runtime.set_state(print_command=False, with_docs=True, with_data=True)
    cfg = json.loads(runtime.mcp_inline())
    assert {"jcodemunch", "jdocmunch", "jdatamunch"} <= set(cfg["mcpServers"].keys())
    runtime.set_state(print_command=False, with_docs=False, with_data=False)


def test_print_command_short_circuits_runner():
    from jragmunch.runner import RunSpec, run

    runtime.set_state(print_command=True)
    res = run(RunSpec(prompt="hi"))
    assert "claude" in res.text.lower() or "claude" in res.text
    assert "-p" in res.text
    runtime.set_state(print_command=False)
