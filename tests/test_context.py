"""Context engineering: relevance-ranked notes + budgeted history."""
from web.backend.agent.context import (
    render_history,
    select_notes,
    topic_cn,
)


def test_topic_cn():
    assert topic_cn("career") == "事业"
    assert topic_cn("unknown-topic") == "这个问题"


def test_select_notes_prefers_current_topic():
    notes = [
        {"topic": "wealth", "conclusion": "财运A"},
        {"topic": "career", "conclusion": "事业B"},
        {"topic": "wealth", "conclusion": "财运C"},
    ]
    picked = select_notes(notes, "wealth", max_notes=2)
    assert [n["conclusion"] for n in picked] == ["财运A", "财运C"]


def test_select_notes_skips_empty_conclusion():
    notes = [
        {"topic": "career", "conclusion": "   "},
        {"topic": "career", "conclusion": "有结论"},
    ]
    assert [n["conclusion"] for n in select_notes(notes, "career")] == ["有结论"]


def test_select_notes_respects_char_budget():
    notes = [
        {"topic": "career", "conclusion": "x" * 400},
        {"topic": "career", "conclusion": "y" * 400},
    ]
    assert len(select_notes(notes, "career", char_budget=500)) == 1


def test_render_history_drops_oldest_to_fit_budget():
    history = [
        {"role": "user", "content": "A" * 100},
        {"role": "assistant", "content": "B" * 100},
        {"role": "user", "content": "C" * 100},
    ]
    out = render_history(history, char_budget=150)
    assert "C" in out and "A" not in out


def test_render_history_empty():
    assert render_history(None) == ""
