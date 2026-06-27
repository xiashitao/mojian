"""LLM-as-judge: score a reply for *fidelity to the engine* + *answer craft*.

The judge never rules on 命理 truth — only whether the reply is consistent with
the deterministic engine's facts and a good answer. Deep model, temperature 0.
"""
from __future__ import annotations

import json
from typing import Any

from web.backend.services.llm import LLMError, complete, is_configured
from web.backend.eval.runner import RunResult

DIMENSIONS = ("切题", "忠于引擎事实", "深度", "边界感", "粒度合规")

_SYSTEM = (
    "你是命理咨询回答的严格质检员。给你三样东西："
    "①「引擎事实」——确定性规则引擎算出的命局结论（用神、格局、相神/忌神、成败、"
    "当前大运流年的喜忌，其中『喜/忌/助用/增凶/平』是引擎对该运/年顺逆的内部判定），"
    "这是**唯一权威的标准答案**；②用户问题；③咨询助手的回答。\n"
    "你不评判命理本身对不对（那不是你的工作），只评判这条回答：是否忠于「引擎事实」、是否答得好。\n"
    "按 1–5 给五个维度打分（5 最好，整数）：\n"
    "- 切题：是否正面回答了用户的问题；\n"
    "- 忠于引擎事实：顺逆判断是否与引擎喜忌一致。**这是最重要的一维**——"
    "若把引擎标为『忌』的大运/流年说成顺、好、有利、利于发展，或把『喜/相神』说成不利，记 1–2 分；\n"
    "- 深度：是否针对这个具体命局（结合具体十神/宫位/五行流向），而非放之四海皆准的空话；\n"
    "- 边界感：是否避免打包票、绝对化（必然/一定应验/必有）、宿命恐吓，保留了不确定性；\n"
    "- 粒度合规：时间最多到『哪一年（流年）』为止，不得细到某月/某日/某季度，不报具体日期吉凶。\n"
    "再根据给定的 must / must_not 期望，逐条判断回答是否满足。\n"
    "只输出严格 JSON，不要任何额外文字：\n"
    '{"scores":{"切题":n,"忠于引擎事实":n,"深度":n,"边界感":n,"粒度合规":n},'
    '"expectations":[{"text":"…","kind":"must|must_not","satisfied":true|false,"reason":"…"}],'
    '"issues":["简短问题点"],"summary":"一句话总评"}'
)


def judge(result: RunResult) -> dict[str, Any]:
    if not is_configured():
        return {"error": "LLM 未配置，无法评分"}
    payload = {
        "引擎事实": result.facts,
        "用户问题": result.case.question,
        "回答": result.reply,
        "must": list(result.case.must),
        "must_not": list(result.case.must_not),
    }
    try:
        raw = complete(_SYSTEM, json.dumps(payload, ensure_ascii=False),
                       temperature=0.0, timeout=120)
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {"error": f"评分返回非对象：{raw[:200]}"}
        return data
    except (LLMError, ValueError, json.JSONDecodeError) as e:
        return {"error": f"评分失败：{e}"}


def overall_score(verdict: dict[str, Any]) -> float | None:
    """Mean of the five dimension scores (None if unscored / errored)."""
    scores = verdict.get("scores") if isinstance(verdict, dict) else None
    if not isinstance(scores, dict):
        return None
    vals = [v for d in DIMENSIONS if isinstance(v := scores.get(d), (int, float))]
    return sum(vals) / len(vals) if vals else None
