"""agent 自主记忆(memory_text)测试:迁移 / 存取 / 净化 / 渲染 / 管线传递。

分层:
1. 列迁移:老库(无 memory_text 列)init_db 后自动补列,老数据可读
2. memory.add_note / recent_notes 存取语义
3. reflect_on_reply 的 memory 字段解析 + 干支净化
4. context.select_notes / render_notes 纳入记忆的渲染与预算
5. planner 传递:generation_trace.memory → 落库(monkeypatch 流式回复)
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from web.backend import database
from web.backend.agent import context, memory, planner, repository, responder
from web.backend.agent.models import BirthInfo, ChatState


@pytest.fixture()
def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "memory.db")
    database.init_db()


# ---------------------------------------------------------------------------
# 1. 列迁移
# ---------------------------------------------------------------------------

class TestColumnMigration:
    def test_legacy_table_gets_memory_text_column(self, tmp_path, monkeypatch):
        """老库没有 memory_text 列:init_db 自动补列,老数据原样可读。"""
        db_path = tmp_path / "legacy.db"
        monkeypatch.setattr(database, "DB_PATH", db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE user_memory_notes (
            id TEXT PRIMARY KEY, memory_key TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT 'self',
            topic TEXT, question TEXT, conclusion TEXT, analysis_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')))""")
        conn.execute("""INSERT INTO user_memory_notes
            (id, memory_key, topic, question, conclusion)
            VALUES ('old1', 'k1', 'career', '问题', '老结论')""")
        conn.commit()
        conn.close()

        database.init_db()  # 触发 _ensure_column

        notes = memory.recent_notes("k1")
        assert len(notes) == 1
        assert notes[0]["conclusion"] == "老结论"
        assert notes[0]["memory_text"] is None  # 老数据补列后为 NULL

    def test_init_db_idempotent_on_new_schema(self, mem_db):
        database.init_db()  # 二次执行不报错(幂等)
        memory.add_note("k", topic="career", question="q", conclusion="c",
                        memory_text="m")
        assert memory.recent_notes("k")[0]["memory_text"] == "m"

    def test_ensure_column_noop_on_missing_table(self, mem_db):
        conn = database.get_db()
        try:
            database._ensure_column(conn, "no_such_table", "x", "TEXT")  # 不炸
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# 2. 存取语义
# ---------------------------------------------------------------------------

class TestAddNoteSemantics:
    def test_memory_text_roundtrip(self, mem_db):
        memory.add_note("k", topic="career", question="想转行",
                        conclusion="明年时机更好", memory_text="35岁想从运营转产品")
        note = memory.recent_notes("k")[0]
        assert note["conclusion"] == "明年时机更好"
        assert note["memory_text"] == "35岁想从运营转产品"

    def test_memory_only_note_is_stored(self, mem_db):
        """conclusion 为空但有记忆 → 也落库(升级前会被丢弃)。"""
        memory.add_note("k", topic="career", question="q",
                        conclusion="", memory_text="正纠结要不要离开体制内")
        notes = memory.recent_notes("k")
        assert len(notes) == 1
        assert notes[0]["memory_text"] == "正纠结要不要离开体制内"

    def test_conclusion_only_note_keeps_old_behaviour(self, mem_db):
        memory.add_note("k", topic="career", question="q",
                        conclusion="只有结论")
        note = memory.recent_notes("k")[0]
        assert note["conclusion"] == "只有结论"
        assert note["memory_text"] is None  # 空记忆存 NULL,不存空串

    def test_both_empty_not_stored(self, mem_db):
        memory.add_note("k", topic="career", question="q",
                        conclusion="", memory_text="  ")
        assert memory.recent_notes("k") == []

    def test_memory_text_truncated_to_200(self, mem_db):
        memory.add_note("k", topic=None, question="q",
                        conclusion="c", memory_text="长" * 500)
        assert len(memory.recent_notes("k")[0]["memory_text"]) == 200

    def test_subject_isolation(self, mem_db):
        memory.add_note("k", topic="career", question="q", conclusion="我的",
                        memory_text="我的记忆", subject="self")
        memory.add_note("k", topic="career", question="q", conclusion="孩子的",
                        memory_text="孩子的记忆", subject="child")
        assert memory.recent_notes("k", "self")[0]["memory_text"] == "我的记忆"
        assert memory.recent_notes("k", "child")[0]["memory_text"] == "孩子的记忆"

    def test_clear_removes_memory_text_rows(self, mem_db):
        memory.add_note("k", topic=None, question="q", conclusion="",
                        memory_text="记住我")
        memory.clear("k")
        assert memory.recent_notes("k") == []


# ---------------------------------------------------------------------------
# 3. reflect_on_reply:memory 字段解析 + 干支净化
# ---------------------------------------------------------------------------

def _fake_complete(payload: dict):
    """构造一个替身 complete(),返回固定 JSON。"""
    def fake(system_prompt, user_prompt, **kw):
        return json.dumps(payload, ensure_ascii=False)
    return fake


class TestReflectMemoryField:
    @pytest.fixture(autouse=True)
    def llm_on(self, monkeypatch):
        monkeypatch.setattr(responder, "is_configured", lambda: True)

    def test_memory_parsed_from_llm_json(self, monkeypatch):
        monkeypatch.setattr(responder, "complete", _fake_complete(
            {"followups": ["然后呢"], "conclusion": "结论", "memory": "用户35岁想转行"}))
        out = responder.reflect_on_reply("career", [], "回复")
        assert out["memory"] == "用户35岁想转行"
        assert out["conclusion"] == "结论"

    def test_missing_memory_field_defaults_empty(self, monkeypatch):
        monkeypatch.setattr(responder, "complete", _fake_complete(
            {"followups": [], "conclusion": "结论"}))
        assert responder.reflect_on_reply("career", [], "回复")["memory"] == ""

    def test_non_string_memory_ignored(self, monkeypatch):
        monkeypatch.setattr(responder, "complete", _fake_complete(
            {"memory": ["列表", "不合法"], "conclusion": "c"}))
        assert responder.reflect_on_reply("career", [], "回复")["memory"] == ""

    def test_ganzhi_stripped_from_memory(self, monkeypatch):
        """干支绝不入库:prompt 已禁,正则兜底(remove the bait)。"""
        monkeypatch.setattr(responder, "complete", _fake_complete(
            {"memory": "用户戊午年生,壬寅运想转行", "conclusion": "c"}))
        out = responder.reflect_on_reply("career", [], "回复")
        assert "戊午" not in out["memory"]
        assert "壬寅" not in out["memory"]
        assert "想转行" in out["memory"]  # 其余内容保留

    def test_no_llm_returns_empty_memory(self, monkeypatch):
        monkeypatch.setattr(responder, "is_configured", lambda: False)
        assert responder.reflect_on_reply("career", [], "回复")["memory"] == ""

    def test_llm_error_returns_empty_memory(self, monkeypatch):
        def boom(*a, **k):
            raise responder.LLMError("down")
        monkeypatch.setattr(responder, "complete", boom)
        assert responder.reflect_on_reply("career", [], "回复")["memory"] == ""


# ---------------------------------------------------------------------------
# 3b. 防重复记录:reflect 看得见已记住的
# ---------------------------------------------------------------------------

class TestMemoryTexts:
    def test_extracts_nonempty_memories(self):
        notes = [
            {"memory_text": "想转行", "conclusion": "c1"},
            {"memory_text": None, "conclusion": "c2"},
            {"memory_text": "  ", "conclusion": "c3"},
            {"memory_text": "备考中", "conclusion": "c4"},
        ]
        assert responder._memory_texts(notes) == ["想转行", "备考中"]

    def test_empty_and_none_notes(self):
        assert responder._memory_texts(None) == []
        assert responder._memory_texts([]) == []


class TestReflectDedup:
    @pytest.fixture(autouse=True)
    def llm_on(self, monkeypatch):
        monkeypatch.setattr(responder, "is_configured", lambda: True)

    def _capture(self, monkeypatch):
        seen = {}

        def fake(system_prompt, user_prompt, **kw):
            seen["system"] = system_prompt
            seen["user"] = user_prompt
            return json.dumps({"followups": [], "conclusion": "", "memory": ""})

        monkeypatch.setattr(responder, "complete", fake)
        return seen

    def test_known_memories_fed_into_prompt(self, monkeypatch):
        seen = self._capture(monkeypatch)
        responder.reflect_on_reply("career", [], "回复",
                                   known_memories=["35岁想转产品", "备考中"])
        payload = json.loads(seen["user"])
        assert payload["已记住的信息"] == ["35岁想转产品", "备考中"]

    def test_system_prompt_forbids_duplicates(self, monkeypatch):
        seen = self._capture(monkeypatch)
        responder.reflect_on_reply("career", [], "回复", known_memories=["x"])
        assert "不要重复记" in seen["system"]

    def test_no_known_memories_sends_empty_list(self, monkeypatch):
        seen = self._capture(monkeypatch)
        responder.reflect_on_reply("career", [], "回复")
        assert json.loads(seen["user"])["已记住的信息"] == []


# ---------------------------------------------------------------------------
# 3c. 画像消费 memory_text
# ---------------------------------------------------------------------------

class TestProfileConsumesMemory:
    def _capture(self, monkeypatch):
        from web.backend.agent import profile as profile_mod
        seen = {}

        def fake(system_prompt, user_prompt, **kw):
            seen["user"] = user_prompt
            return json.dumps({})

        monkeypatch.setattr(profile_mod, "is_configured", lambda: True)
        monkeypatch.setattr(profile_mod, "complete", fake)
        return profile_mod, seen

    def test_memory_text_marked_as_user_statement(self, monkeypatch):
        profile_mod, seen = self._capture(monkeypatch)
        notes = [{"topic": "career", "question": "想转行吗", "conclusion": "明年更稳",
                  "memory_text": "35岁想转产品"}]
        profile_mod.build_or_update_profile(None, notes, [])
        assert "用户自述:35岁想转产品" in seen["user"]

    def test_legacy_note_line_format_unchanged(self, monkeypatch):
        profile_mod, seen = self._capture(monkeypatch)
        notes = [{"topic": "career", "question": "问题", "conclusion": "结论",
                  "memory_text": None}]
        profile_mod.build_or_update_profile(None, notes, [])
        assert "[事业] 问:问题 → 结论:结论" in seen["user"]
        assert "用户自述" not in seen["user"]


# ---------------------------------------------------------------------------
# 4. 渲染与预算
# ---------------------------------------------------------------------------

class TestRenderNotes:
    def test_conclusion_with_memory_rendered_together(self):
        notes = [{"topic": "career", "conclusion": "明年更稳",
                  "memory_text": "35岁想转产品"}]
        text = context.render_notes(notes, "career")
        assert "明年更稳" in text
        assert "用户情况：35岁想转产品" in text

    def test_memory_only_note_rendered(self):
        notes = [{"topic": "career", "conclusion": "",
                  "memory_text": "正准备考研"}]
        text = context.render_notes(notes, "career")
        assert "用户情况：正准备考研" in text

    def test_conclusion_only_format_unchanged(self):
        """无记忆的老笔记,渲染格式与升级前完全一致(不带「用户情况」)。"""
        notes = [{"topic": "career", "conclusion": "老结论", "memory_text": None}]
        assert context.render_notes(notes, "career") == "[事业] 老结论"

    def test_empty_notes_render_empty(self):
        assert context.render_notes([], "career") == ""
        assert context.render_notes(None, "career") == ""

    def test_same_topic_ranked_first(self):
        notes = [
            {"topic": "love", "conclusion": "感情结论", "memory_text": None},
            {"topic": "career", "conclusion": "事业结论", "memory_text": None},
        ]
        lines = context.render_notes(notes, "career").splitlines()
        assert lines[0] == "[事业] 事业结论"

    def test_budget_counts_memory_text(self):
        """预算按完整渲染行算:带长记忆的笔记会更早触达预算上限。"""
        long_memory = "长记忆" * 60  # 180 字
        notes = [
            {"topic": "career", "conclusion": "结论一", "memory_text": long_memory},
            {"topic": "career", "conclusion": "结论二", "memory_text": long_memory},
            {"topic": "career", "conclusion": "结论三", "memory_text": long_memory},
            {"topic": "career", "conclusion": "结论四", "memory_text": long_memory},
        ]
        picked = context.select_notes(notes, "career")
        # 每行约 190 字,预算 600 → 只能装下 3 条(第一条永远保留)
        assert 1 <= len(picked) < 4

    def test_memory_only_note_passes_content_filter(self):
        notes = [{"topic": "career", "conclusion": "", "memory_text": "有记忆"}]
        assert len(context.select_notes(notes, "career")) == 1

    def test_truly_empty_note_filtered(self):
        notes = [{"topic": "career", "conclusion": "", "memory_text": None}]
        assert context.select_notes(notes, "career") == []


# ---------------------------------------------------------------------------
# 5. planner 传递:generation_trace.memory → 落库
# ---------------------------------------------------------------------------

@pytest.fixture()
def agent_db(tmp_path, monkeypatch):
    """隔离 DB + 强制 LLM 降级(密闭,不烧真 key)。"""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "agent.db")
    database.init_db()
    from web.backend.agent import extractor
    from web.backend.services import llm
    for mod in (extractor, responder, llm):
        monkeypatch.setattr(mod, "is_configured", lambda: False)


def _fake_stream(reply="模拟回复", conclusion="模拟结论", memory_note="用户想转行"):
    """替身 stream_consultation_reply:一段回复 + 带 memory 的 generation_trace。"""
    def fake(topic, tool_result, **kw):
        state = ChatState(topic=topic, needs_more_info=False,
                          missing_fields=[], suggested_followups=[])
        trace = {"mode": "fake", "conclusion": conclusion, "memory": memory_note}
        yield reply, None, None
        yield "", state, trace
    return fake


class TestPlannerMemoryFlow:
    BIRTH_MSG = "1990年5月15日早上8点北京男，看事业"

    def test_memory_from_generation_trace_persisted(self, agent_db, monkeypatch):
        monkeypatch.setattr(planner, "stream_consultation_reply", _fake_stream())
        list(planner.stream_chat(self.BIRTH_MSG, memory_key="u1"))
        note = memory.recent_notes("u1")[0]
        assert note["conclusion"] == "模拟结论"
        assert note["memory_text"] == "用户想转行"

    def test_memory_only_trace_still_persisted(self, agent_db, monkeypatch):
        """conclusion 空但有记忆 → 照样落库(升级前这轮会整个丢弃)。"""
        monkeypatch.setattr(planner, "stream_consultation_reply",
                            _fake_stream(conclusion="", memory_note="只记情况"))
        list(planner.stream_chat(self.BIRTH_MSG, memory_key="u2"))
        note = memory.recent_notes("u2")[0]
        assert note["memory_text"] == "只记情况"

    def test_no_conclusion_no_memory_writes_nothing(self, agent_db, monkeypatch):
        monkeypatch.setattr(planner, "stream_consultation_reply",
                            _fake_stream(conclusion="", memory_note=""))
        list(planner.stream_chat(self.BIRTH_MSG, memory_key="u3"))
        assert memory.recent_notes("u3") == []

    def test_update_memory_trace_records_memory(self, agent_db, monkeypatch):
        monkeypatch.setattr(planner, "stream_consultation_reply", _fake_stream())
        chunks = [json.loads(c) for c in
                  planner.stream_chat(self.BIRTH_MSG, memory_key="u4")]
        done = chunks[-1]
        package = repository.get_analysis_package(done["analysis_id"])
        update_steps = [t for t in package["run_traces"]
                        if t["step_type"] == "update_memory"]
        assert len(update_steps) == 1
        assert update_steps[0]["output_json"]["memory"] == "用户想转行"

    def test_next_turn_prompt_would_contain_memory(self, agent_db, monkeypatch):
        """下一轮取 notes 渲染,能看到上一轮的 agent 记忆。"""
        monkeypatch.setattr(planner, "stream_consultation_reply", _fake_stream())
        list(planner.stream_chat(self.BIRTH_MSG, memory_key="u5"))
        notes = memory.recent_notes("u5")
        rendered = context.render_notes(notes, "career")
        assert "用户情况：用户想转行" in rendered
