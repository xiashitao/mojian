"""话题注册表（topic-as-data）及其与 prompt 组装的契约。"""
import json
import re
from typing import get_args

from web.backend.agent.models import Topic
from web.backend.agent.responder import _build_stream_reply_prompt
from web.backend.agent.topics import TOPICS, all_key_ages, topic_cn, topic_spec

_GANZHI_RE = re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]")


def test_registry_covers_topic_literal():
    # 注册表与 models.Topic 同步：新增话题必须两边一起加。
    assert set(TOPICS) == set(get_args(Topic))


def test_topic_cn_preserves_legacy_behavior():
    assert topic_cn("career") == "事业"
    assert topic_cn(None) == "事业"
    assert topic_cn("unknown-topic") == "这个问题"


def test_key_ages_union():
    # 现网行为锚点：升学考节点 15/18/22。调整话题 key_ages 时有意识地更新这里。
    assert all_key_ages() == (15, 18, 22)


def test_emphasis_respects_prompt_rules():
    for spec in TOPICS.values():
        # 侧重段不得泄漏干支、不得细过流年（不许出现月/日粒度的判断承诺）。
        assert not _GANZHI_RE.search(spec.emphasis), spec.key
        assert spec.emphasis.strip()
        assert spec.followups  # 兜底追问池非空


def _prompt_for(topic):
    context = {
        "day_master": "丁", "day_master_element": "火",
        "strength_verdict": "身强", "ge_ju": "正官格",
        "yong_shen_ten_god": "正官", "cheng_bai": "成",
        "has_unresolved_cases": False, "arbitration_decisions": {},
        "four_pillars": {}, "wuxing": {}, "natal_interactions": [],
        "luck_sequence": [], "current_period": None,
        "source_basis": {},
    }
    return _build_stream_reply_prompt(topic, context, clarify_previous=False,
                                      user_message="帮我看看")


def test_emphasis_lands_in_volatile_tail():
    p = _prompt_for("career")
    assert topic_spec("career").emphasis in p["user_prompt"]
    # 侧重段必须在「用户当前的问题」的反注入段之前，否则会被当用户内容作废。
    assert p["user_prompt"].index(topic_spec("career").emphasis) < \
        p["user_prompt"].index("## 用户当前的问题")
    # system prompt 保持话题无关（前缀缓存约束）。
    assert topic_spec("career").emphasis not in p["system_prompt"]


def test_analysis_block_byte_identical_across_topics():
    # 换话题只允许改易变尾部：结构化分析结果 JSON 必须逐字节一致（前缀缓存）。
    def analysis_json(p):
        body = p["user_prompt"]
        start = body.index("## 结构化分析结果")
        end = body.index("## 本轮分析侧重")
        return body[start:end]

    a = _prompt_for("career")
    b = _prompt_for("wealth")
    assert analysis_json(a) == analysis_json(b)
    assert a["system_prompt"] == b["system_prompt"]
    json.loads(analysis_json(a).split("## 结构化分析结果")[1])  # 仍是合法 JSON
