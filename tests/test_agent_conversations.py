import json

import pytest

from web.backend import database
from web.backend.agent import planner, repository


@pytest.fixture()
def agent_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "agent.db")
    database.init_db()


def test_stream_chat_records_assistant_message_id(agent_db):
    chunks = list(planner.stream_chat("你好"))
    done = json.loads(chunks[-1])

    package = repository.get_analysis_package(done["analysis_id"])

    assert package is not None
    assistant_message_id = package["agent_run"]["assistant_message_id"]
    assistant_message_ids = {
        message["id"]
        for message in package["messages"]
        if message["role"] == "assistant"
    }
    assert assistant_message_id in assistant_message_ids


def _stream_text(message: str) -> tuple[str, dict]:
    chunks = [json.loads(c) for c in planner.stream_chat(message)]
    text = "".join(c.get("text", "") for c in chunks if c.get("type") == "token")
    return text, chunks[-1]


def test_stream_chat_smalltalk_skips_chart(agent_db):
    text, done = _stream_text("你好")
    assert "结合命理看" in text  # smalltalk reply, not a chart consultation
    assert done["state"]["needs_more_info"] is False


def test_stream_chat_out_of_scope_redirects(agent_db):
    text, _ = _stream_text("帮我选只股票")
    assert "超出" in text


def test_memory_seeds_birth_info_for_returning_user(agent_db):
    key = "anon-returning-user"
    # First conversation: provide complete birth info (gets remembered).
    list(planner.stream_chat("1990年5月15日早上8点北京男，看事业", memory_key=key))
    # New conversation with no birth info in the message — memory should fill it.
    text, done = _stream_text_keyed("看看我的财运", memory_key=key)
    assert "出生" not in text  # did not re-ask for birth info
    assert done["state"]["needs_more_info"] is False
    assert done["state"]["topic"] == "wealth"


def _stream_text_keyed(message: str, *, memory_key: str) -> tuple[str, dict]:
    chunks = [json.loads(c) for c in planner.stream_chat(message, memory_key=memory_key)]
    text = "".join(c.get("text", "") for c in chunks if c.get("type") == "token")
    return text, chunks[-1]


def test_get_conversation_returns_owner_for_authorization_checks(agent_db):
    conversation = repository.ensure_conversation(None, user_id="owner-user")
    repository.add_message(conversation["id"], "user", "测试")

    stored = repository.get_conversation(conversation["id"])

    assert stored is not None
    assert stored["user_id"] == "owner-user"
