from jragmunch.defaults import HAIKU, SONNET, for_verb


def test_ask_defaults_to_haiku_with_low_turn_cap():
    model, turns = for_verb("ask")
    assert model == HAIKU
    assert 1 <= turns <= 8


def test_review_defaults_to_sonnet_with_higher_turn_cap():
    model, turns = for_verb("review")
    assert model == SONNET
    assert turns >= 10


def test_unknown_verb_falls_back():
    model, turns = for_verb("xyz")
    assert model == HAIKU


def test_runspec_emits_max_turns():
    from jragmunch.runner import RunSpec, build_argv

    argv = build_argv(RunSpec(prompt="x", max_turns=6))
    assert "--max-turns" in argv
    idx = argv.index("--max-turns")
    assert argv[idx + 1] == "6"
