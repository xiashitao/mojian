"""用户反馈链路:按 analysis_id 落库(归属校验)+ admin 定位列表。

闭环:普通用户赞/踩(可带评论)→ 存进助手消息 metadata_json →
运营从 list_feedback / obs_cli feedback 看到差评 → 拿 analysis_id 开 trace。
"""
from __future__ import annotations

import json

import pytest

from web.backend import database
from web.backend.agent import planner, repository, responder


OWNER = "fb-user"


@pytest.fixture()
def agent_db(tmp_path, monkeypatch):
    """隔离 DB + 强制 LLM 降级(密闭)。"""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "agent.db")
    database.init_db()
    from web.backend.agent import extractor
    from web.backend.services import llm
    for mod in (extractor, responder, llm):
        monkeypatch.setattr(mod, "is_configured", lambda: False)


@pytest.fixture()
def analysis_id(agent_db) -> str:
    """跑一轮真实对话,返回其 analysis_id(会话归属 OWNER)。"""
    chunks = [json.loads(c) for c in planner.stream_chat("你好", memory_key=OWNER)]
    return chunks[-1]["analysis_id"]


def _stored_meta(analysis_id: str) -> dict:
    """直接读库:该轮助手消息的 metadata_json。"""
    package = repository.get_analysis_package(analysis_id)
    mid = package["agent_run"]["assistant_message_id"]
    msg = next(m for m in package["messages"] if m["id"] == mid)
    meta = msg["metadata_json"]
    return meta if isinstance(meta, dict) else json.loads(meta or "{}")


class TestSetFeedback:
    def test_like_persisted_to_message_metadata(self, analysis_id):
        out = repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="like")
        assert out == {"analysis_id": analysis_id, "feedback": "like"}
        meta = _stored_meta(analysis_id)
        assert meta["feedback"] == "like"
        assert meta["feedback_at"]

    def test_dislike_with_comment(self, analysis_id):
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER,
            feedback="dislike", comment="年份说错了")
        meta = _stored_meta(analysis_id)
        assert meta["feedback"] == "dislike"
        assert meta["feedback_comment"] == "年份说错了"

    def test_comment_truncated_to_500(self, analysis_id):
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="dislike", comment="长" * 900)
        assert len(_stored_meta(analysis_id)["feedback_comment"]) == 500

    def test_none_revokes_feedback_and_comment(self, analysis_id):
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="dislike", comment="不对")
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback=None)
        meta = _stored_meta(analysis_id)
        assert "feedback" not in meta
        assert "feedback_comment" not in meta
        assert "feedback_at" not in meta

    def test_update_replaces_previous_comment(self, analysis_id):
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="dislike", comment="旧评论")
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="like")  # 无评论的更新
        meta = _stored_meta(analysis_id)
        assert meta["feedback"] == "like"
        assert "feedback_comment" not in meta  # 旧评论不残留

    def test_feedback_does_not_clobber_existing_metadata(self, analysis_id):
        """metadata_json 里已有的 followups/conclusion 等字段不能被反馈冲掉。"""
        before = _stored_meta(analysis_id)
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="like")
        after = _stored_meta(analysis_id)
        for key, value in before.items():
            assert after.get(key) == value


class TestOwnership:
    def test_wrong_owner_rejected(self, analysis_id):
        assert repository.set_message_feedback(
            analysis_id, owner_key="someone-else", feedback="like") is None
        assert "feedback" not in _stored_meta(analysis_id)

    def test_missing_owner_rejected(self, analysis_id):
        assert repository.set_message_feedback(
            analysis_id, owner_key=None, feedback="like") is None

    def test_unknown_analysis_rejected(self, agent_db):
        assert repository.set_message_feedback(
            "an_does_not_exist", owner_key=OWNER, feedback="like") is None


class TestFeedbackList:
    def test_empty_when_no_feedback(self, analysis_id):
        assert repository.list_feedback() == []

    def test_lists_feedback_with_locating_fields(self, analysis_id):
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="dislike", comment="答非所问")
        rows = repository.list_feedback()
        assert len(rows) == 1
        row = rows[0]
        # 定位三件套:反馈内容 + analysis_id(开 trace)+ 上下文摘录
        assert row["feedback"] == "dislike"
        assert row["comment"] == "答非所问"
        assert row["analysis_id"] == analysis_id
        assert row["conversation_id"]
        assert row["user_message"] == "你好"
        assert row["reply_excerpt"]

    def test_revoked_feedback_not_listed(self, analysis_id):
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="like")
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback=None)
        assert repository.list_feedback() == []

    def test_days_window_filters(self, analysis_id):
        repository.set_message_feedback(
            analysis_id, owner_key=OWNER, feedback="like")
        assert len(repository.list_feedback(days=365)) == 1
