"""Routing-decision logic (LLM-free path)."""
from web.backend.agent.models import BirthInfo, ConversationState
from web.backend.agent.router import _action_for, route

COMPLETE = BirthInfo(
    birth_date="1990-05-15", birth_time="08:30", longitude=116.4, gender="male"
)


def test_smalltalk_and_out_of_scope_win_over_state():
    assert _action_for("smalltalk", "career", COMPLETE) == "smalltalk"
    assert _action_for("out_of_scope", None, COMPLETE) == "out_of_scope"


def test_incomplete_birth_info_gates_everything():
    assert _action_for("career", "career", BirthInfo()) == "ask_birth_info"
    assert _action_for("clarify_previous", "career", BirthInfo()) == "ask_birth_info"


def test_ask_topic_when_complete_but_no_topic():
    assert _action_for("collect_birth_info", None, COMPLETE) == "ask_topic"
    assert _action_for("unknown", None, COMPLETE) == "ask_topic"


def test_consult_and_clarify():
    assert _action_for("career", "career", COMPLETE) == "consult"
    assert _action_for("clarify_previous", "career", COMPLETE) == "clarify"


def test_route_greeting():
    assert route("你好", ConversationState()).action == "smalltalk"


def test_route_consults_with_complete_state():
    state = ConversationState(birth_info=COMPLETE, current_topic="career")
    decision = route("适合单干还是合伙", state)
    assert decision.action == "consult"
    assert decision.topic == "career"
