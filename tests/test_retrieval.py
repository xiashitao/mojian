"""笔记检索测试:词法原语 / 近重复折叠 / 无query兼容 / 查询感知排序 / 候选池。

设计意图(select_notes):
- 词法命中是强信号:用户这句话提到的旧信息要能跨话题被捞回来
- 话题标签是弱先验;时间是并列时的裁决
- 近重复折叠是存储侧 reflect 去重之外的第二道闸
- 无 query 时行为与旧版一致(兼容不带查询的调用方)
"""
from __future__ import annotations

import pytest

from web.backend.agent import context
from web.backend.agent.context import (
    _bigrams,
    _lexical_sim,
    _norm,
    render_notes,
    select_notes,
)


def _note(topic="career", conclusion="", memory=None):
    return {"topic": topic, "conclusion": conclusion, "memory_text": memory}


# ---------------------------------------------------------------------------
# 1. 词法原语
# ---------------------------------------------------------------------------

class TestLexicalPrimitives:
    def test_norm_strips_punctuation_and_space(self):
        assert _norm("父亲，有  心脏病！") == "父亲有心脏病"

    def test_norm_lowercases_latin(self):
        assert _norm("MBA 备考") == "mba备考"

    def test_norm_empty_and_none(self):
        assert _norm("") == ""
        assert _norm(None) == ""

    def test_bigrams_chinese(self):
        assert _bigrams("心脏病") == {"心脏", "脏病"}

    def test_bigrams_single_char(self):
        assert _bigrams("心") == {"心"}

    def test_bigrams_empty(self):
        assert _bigrams("") == set()

    def test_sim_identical_is_one(self):
        g = _bigrams("父亲有心脏病")
        assert _lexical_sim(g, g) == 1.0

    def test_sim_disjoint_is_zero(self):
        assert _lexical_sim(_bigrams("心脏病"), _bigrams("换工作")) == 0.0

    def test_sim_partial_between_zero_and_one(self):
        s = _lexical_sim(_bigrams("父亲心脏病"), _bigrams("父亲有心脏病史需要复查"))
        assert 0.0 < s < 1.0

    def test_sim_empty_operand_is_zero(self):
        assert _lexical_sim(set(), _bigrams("x")) == 0.0


# ---------------------------------------------------------------------------
# 2. 近重复折叠
# ---------------------------------------------------------------------------

class TestDedup:
    def test_near_identical_collapsed_keep_newest(self):
        notes = [  # 新→旧
            _note(conclusion="今年宜守财,避免冲动消费"),
            _note(conclusion="今年宜守财，避免冲动消费。"),  # 仅标点差异
        ]
        picked = select_notes(notes, "career")
        assert len(picked) == 1
        assert picked[0] is notes[0]      # 保留最新那条

    def test_distinct_notes_all_kept(self):
        notes = [
            _note(conclusion="今年宜守财"),
            _note(conclusion="明年适合转型"),
        ]
        assert len(select_notes(notes, "career")) == 2

    def test_dedup_sees_memory_text(self):
        """conclusion 不同但整行(含记忆)高度相似 → 折叠。"""
        notes = [
            _note(conclusion="宜守财", memory="35岁想从运营转产品经理岗位"),
            _note(conclusion="宜守财", memory="35岁想从运营转产品经理岗"),
        ]
        assert len(select_notes(notes, "career")) == 1


# ---------------------------------------------------------------------------
# 3. 无 query:旧行为兼容
# ---------------------------------------------------------------------------

class TestNoQueryCompat:
    def test_same_topic_first_then_newest(self):
        notes = [  # 新→旧
            _note(topic="love", conclusion="感情新"),
            _note(topic="career", conclusion="事业新"),
            _note(topic="career", conclusion="事业旧"),
        ]
        picked = select_notes(notes, "career")
        assert [n["conclusion"] for n in picked] == ["事业新", "事业旧", "感情新"]

    def test_empty_query_string_same_as_no_query(self):
        notes = [_note(topic="love", conclusion="a"), _note(conclusion="b")]
        assert select_notes(notes, "career", query="") == \
               select_notes(notes, "career")

    def test_punctuation_only_query_treated_as_empty(self):
        notes = [_note(topic="love", conclusion="a"), _note(conclusion="b")]
        assert select_notes(notes, "career", query="？！") == \
               select_notes(notes, "career")


# ---------------------------------------------------------------------------
# 4. 查询感知排序
# ---------------------------------------------------------------------------

class TestQueryAwareRanking:
    def test_keyword_hit_beats_topic_only(self):
        """跨话题捞回:当前问财务,但这句话提到的旧事业笔记(含家人健康背景)
        要压过更新的同话题笔记。注:健康是拒答话题,不会有 health 笔记——
        健康信息只会作为「背景」记在其他话题的笔记里,这正是真实场景。"""
        notes = [  # 新→旧;当前话题 wealth
            _note(topic="wealth", conclusion="今年宜守财深耕"),
            _note(topic="career", conclusion="回老家发展时机未到",
                  memory="父亲有心脏病史,纠结要不要回老家工作"),
        ]
        picked = select_notes(notes, "wealth",
                              query="父亲心脏病最近又犯了,我是不是该回老家")
        assert picked[0]["memory_text"].startswith("父亲有心脏病")

    def test_query_matches_memory_text_too(self):
        """记忆里的信息也参与词法匹配(整行打分)。"""
        notes = [
            _note(topic="career", conclusion="宜守财"),
            _note(topic="career", conclusion="时机未到", memory="正在准备MBA备考"),
        ]
        picked = select_notes(notes, "career", query="MBA备考压力很大")
        assert picked[0]["memory_text"] == "正在准备MBA备考"

    def test_recency_breaks_ties(self):
        """相关性相同(都不沾边)时,新的在前。"""
        notes = [
            _note(topic="career", conclusion="新结论内容甲"),
            _note(topic="career", conclusion="旧结论内容乙"),
        ]
        picked = select_notes(notes, "career", query="完全无关的问题内容")
        assert picked[0]["conclusion"] == "新结论内容甲"

    def test_topic_still_matters_without_keyword(self):
        """query 与谁都不沾边时,同话题标签仍是先验。"""
        notes = [
            _note(topic="love", conclusion="感情的结论"),
            _note(topic="career", conclusion="事业的结论"),
        ]
        picked = select_notes(notes, "career", query="嗯再帮我看看呗")
        assert picked[0]["topic"] == "career"

    def test_budget_respected_with_query(self):
        long = "长" * 300
        notes = [_note(conclusion=f"{long}{i}") for i in range(4)]
        picked = select_notes(notes, "career", query="长长长")
        assert len(picked) < 4              # 600 字预算装不下 4 条
        assert len(picked) >= 1             # 第一条永远保留

    def test_deterministic_same_input_same_output(self):
        notes = [_note(topic="career", conclusion=f"结论{i}") for i in range(6)]
        q = "看看结论3相关的"
        assert select_notes(notes, "career", query=q) == \
               select_notes(notes, "career", query=q)


# ---------------------------------------------------------------------------
# 5. render_notes 透传 + 端到端形状
# ---------------------------------------------------------------------------

class TestRenderWithQuery:
    def test_query_reorders_rendered_lines(self):
        notes = [
            _note(topic="wealth", conclusion="今年宜守财深耕"),
            _note(topic="career", conclusion="回老家发展时机未到",
                  memory="父亲有心脏病史,纠结要不要回老家工作"),
        ]
        text = render_notes(notes, "wealth", query="父亲心脏病最近又犯了,该回老家吗")
        lines = text.splitlines()
        assert lines[0].startswith("[事业]") and "心脏病" in lines[0]

    def test_no_query_render_format_unchanged(self):
        notes = [_note(topic="career", conclusion="老结论", memory=None)]
        assert render_notes(notes, "career") == "[事业] 老结论"


# ---------------------------------------------------------------------------
# 6. planner 候选池:取 30 条供精选
# ---------------------------------------------------------------------------

class TestCandidatePool:
    def test_planner_fetches_wide_pool(self, tmp_path, monkeypatch):
        import json as _json

        from web.backend import database
        from web.backend.agent import memory, planner, responder
        from web.backend.agent.models import ChatState

        monkeypatch.setattr(database, "DB_PATH", tmp_path / "agent.db")
        database.init_db()
        from web.backend.agent import extractor
        from web.backend.services import llm
        for mod in (extractor, responder, llm):
            monkeypatch.setattr(mod, "is_configured", lambda: False)

        key = "pool-user"
        for i in range(12):
            memory.add_note(key, topic="career", question=f"q{i}",
                            conclusion=f"第{i}轮的独立结论内容")

        seen = {}

        def fake_stream(topic, tool_result, **kw):
            seen["notes"] = kw.get("memory_notes") or []
            state = ChatState(topic=topic, needs_more_info=False,
                              missing_fields=[], suggested_followups=[])
            yield "回复", None, None
            yield "", state, {"mode": "fake", "conclusion": "", "memory": ""}

        monkeypatch.setattr(planner, "stream_consultation_reply", fake_stream)
        list(planner.stream_chat("1990年5月15日早上8点北京男，看事业",
                                 memory_key=key))
        assert len(seen["notes"]) == 12     # 候选池不再截到 5 条
