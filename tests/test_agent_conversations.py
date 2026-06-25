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


def test_get_conversation_returns_owner_for_authorization_checks(agent_db):
    conversation = repository.ensure_conversation(None, user_id="owner-user")
    repository.add_message(conversation["id"], "user", "测试")

    stored = repository.get_conversation(conversation["id"])

    assert stored is not None
    assert stored["user_id"] == "owner-user"
