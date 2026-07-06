"""用户画像的生成与更新。

每 N 轮咨询后,用 fast 模型回顾最近的笔记和对话,提取/更新用户的稳定
特征(人生阶段、核心关切、性格、目标、沟通偏好),merge 进现有画像。

设计原则(写进 prompt 反复强调):
- 只记录对话里「明确出现」的信号,绝不臆测。
- 保守更新:新信息与旧画像冲突时,以最近、最明确的为准;没有新信号
  就原样保留旧字段,不要"为了更新而更新"。
- 画像仅供参考,回答时照顾它但不被它框死。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ..services.llm import LLMError, complete, fast_provider, is_configured
from .context import render_history, topic_cn
from .models import UserProfile

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你在为一个命理咨询助手维护「用户画像」——对这个用户的稳定认知,用于让后续回答更贴合他/她。

你会收到:
1. 当前画像(可能为空)
2. 这位用户最近的咨询记录(每条含话题、问题、一句话结论)
3. 最近的对话片段

请输出严格 JSON,字段如下(全部可空,没把握就留 null 或空数组):
- life_stage:人生阶段。如「在校」「职场初期」「职业转型期」「创业」「家庭主妇」「退休」等。
- core_concerns:字符串数组,核心关切。来自用户反复追问、明确表达焦虑或目标的话题。如 ["职业方向","婚姻","父母健康"]。最多 5 个。
- traits:字符串数组,性格关键词。从用户的言谈方式、决策倾向里提取,如 ["谨慎","重家庭","理想主义","行动派"]。最多 6 个,每个不超过 6 字。
- long_term_goal:一句话长期目标,如「希望在 35 岁前完成职业转型」。没有明确目标就 null。
- comm_style:沟通偏好,从「直接」「委婉」「理性」「感性」「简洁」「详细」里选最贴切的 1-2 个,没有信号就 null。
- raw_summary:一句话补充描述,放结构化字段装不下的细节。没把握就 null。

## 铁律
1. 只记录对话里「明确出现」的信号。用户没明说,你就不写——宁可画像空白,绝不臆测。
2. 保守更新:有新且明确的信号就更新对应字段;没新信号就保留当前画像的原值。
3. 冲突时以最近、最明确的表达为准(人会变,画像要跟上)。
4. 不要为了"显得了解"而编造。空画像完全 OK,它只意味着我们对这个用户还不了解。
5. 只输出 JSON,不要任何解释。"""


def build_or_update_profile(
    current: UserProfile | None,
    recent_notes: list[dict[str, Any]] | None,
    recent_history: list[dict[str, Any]] | None,
) -> UserProfile:
    """用 fast 模型,从最近 N 轮的笔记+对话里提取画像信号,merge 进现有画像。

    失败时(没配 LLM / 调用出错 / JSON 解析失败)优雅降级:返回当前画像
    原值(若有),否则空画像。绝不抛异常阻塞主流程。
    """
    fallback = current or UserProfile()

    # 没有可用输入(笔记和对话都空)→ 没什么可提取的,直接返回。
    if not recent_notes and not recent_history:
        return fallback

    if not is_configured():
        return fallback

    user_prompt = _build_user_prompt(current, recent_notes, recent_history)

    try:
        raw = complete(
            _SYSTEM_PROMPT,
            user_prompt,
            temperature=0.2,  # 低温度:画像抽取要稳定、可复现,不要发散
            provider=fast_provider(),
        )
        data = json.loads(raw)
        if not isinstance(data, dict):
            return fallback
        return _profile_from_llm(data, fallback)
    except (LLMError, json.JSONDecodeError, ValueError, TypeError) as e:
        log.warning("profile update failed, keeping current: %s", e)
        return fallback


def _build_user_prompt(
    current: UserProfile | None,
    notes: list[dict[str, Any]] | None,
    history: list[dict[str, Any]] | None,
) -> str:
    """Assemble the LLM input: current profile + recent notes + recent dialogue."""
    parts: list[str] = []

    # 1. 当前画像
    if current and not current.is_empty():
        parts.append("## 当前画像(在此基础上更新,没新信号就保留)")
        parts.append(json.dumps(_profile_to_dict(current), ensure_ascii=False, indent=2))
    else:
        parts.append("## 当前画像")
        parts.append("(空——这是首次为该用户建立画像)")

    # 2. 最近的咨询记录(笔记)
    if notes:
        parts.append("## 最近的咨询记录(用户聊过的话题和结论)")
        lines: list[str] = []
        for n in notes:
            topic = topic_cn(n.get("topic")) if n.get("topic") else "未分类"
            question = str(n.get("question", "")).strip()[:60]
            conclusion = str(n.get("conclusion", "")).strip()
            lines.append(f"[{topic}] 问:{question} → 结论:{conclusion}")
        parts.append("\n".join(lines))

    # 3. 最近的对话(让模型看到用户的原话和语气)
    transcript = render_history(history)
    if transcript:
        parts.append("## 最近的对话原文(观察用户的表达方式和关注点)")
        parts.append(transcript)

    parts.append("## 请输出更新后的完整画像 JSON")
    return "\n\n".join(parts)


def _profile_to_dict(p: UserProfile) -> dict[str, Any]:
    """Compact dict for the prompt (omit empty fields to save tokens)."""
    d: dict[str, Any] = {}
    if p.life_stage:
        d["life_stage"] = p.life_stage
    if p.core_concerns:
        d["core_concerns"] = p.core_concerns
    if p.traits:
        d["traits"] = p.traits
    if p.long_term_goal:
        d["long_term_goal"] = p.long_term_goal
    if p.comm_style:
        d["comm_style"] = p.comm_style
    if p.raw_summary:
        d["raw_summary"] = p.raw_summary
    return d


def _profile_from_llm(data: dict[str, Any], fallback: UserProfile) -> UserProfile:
    """Parse LLM JSON into a UserProfile, validating types and clamping sizes."""
    def as_str(key: str) -> str | None:
        v = data.get(key)
        s = str(v).strip() if v is not None else ""
        return s or None

    def as_str_list(key: str, max_items: int) -> list[str]:
        v = data.get(key)
        if not isinstance(v, list):
            return []
        items = [str(x).strip() for x in v if str(x).strip()]
        return items[:max_items]

    profile = UserProfile(
        life_stage=as_str("life_stage"),
        core_concerns=as_str_list("core_concerns", max_items=5),
        traits=as_str_list("traits", max_items=6),
        long_term_goal=as_str("long_term_goal"),
        comm_style=as_str("comm_style"),
        raw_summary=as_str("raw_summary"),
    )

    # LLM 若把所有字段都返回空(没新信号),保留 fallback 而不是覆盖成空。
    # 这是"保守更新"的最后一道防线:不因 LLM 一次空响应就清掉已积累的画像。
    if profile.is_empty():
        return fallback
    return profile
