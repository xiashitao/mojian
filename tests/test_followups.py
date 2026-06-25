"""History-aware follow-up suggestions (LLM-free fallback)."""
from web.backend.agent.responder import _FOLLOWUP_POOL, _followups


def test_excludes_already_asked():
    asked = _FOLLOWUP_POOL["career"][0]
    history = [
        {"role": "user", "content": asked},
        {"role": "assistant", "content": "..."},
    ]
    result = _followups("career", history)
    assert asked not in result
    assert len(result) == 3


def test_varies_across_turns():
    first = _followups("career", [])
    later = _followups("career", [{"role": "assistant", "content": "..."}])
    assert first != later


def test_defaults_to_personality_for_unknown_topic():
    assert len(_followups(None, [])) == 3
