"""带偏攻击 eval——打真实的 route→respond 链路，量化四道防线挡不挡得住。

与 run.py（单轮、善意提问）互补：这里每个用例带脚本化的多轮历史和会话状态，
先看 router 的确定性判定（action/topic 是否符合预期），再看生成回复是否守住
must/must_not。判 PASS 的标准：路由正确 + 无 grounding 违规 + 期望全满足。

    PYTHONPATH=. python -m web.backend.eval.attack_run                # 全部
    PYTHONPATH=. python -m web.backend.eval.attack_run flip-deny      # 按 id
    PYTHONPATH=. python -m web.backend.eval.attack_run out-of-scope   # 按类别
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from bazibase import solar_ganzhi_year

from web.backend.agent.models import ConversationState
from web.backend.agent.responder import (
    build_out_of_scope_reply,
    build_smalltalk_reply,
    stream_consultation_reply,
)
from web.backend.agent.router import route
from web.backend.agent.tools import run_bazibase_tools
from web.backend.eval.attacks import ANCHOR_BIRTH, ATTACKS, ATTACKS_BY_ID, AttackCase
from web.backend.eval.cases import EvalCase
from web.backend.eval.judge import judge, overall_score
from web.backend.eval.runner import _SOURCE_BASIS, RunResult, engine_facts
from web.backend.services.llm import is_configured

_REPORT_DIR = Path(__file__).parent / "reports"

CATEGORIES = ("topic-jump", "out-of-scope", "pressure-flip", "granularity")


@dataclass
class AttackResult:
    case: AttackCase
    action: str
    topic: str | None
    routing_ok: bool
    reply: str
    reply_mode: str  # llm | deterministic | none
    grounding_violations: list[str] = field(default_factory=list)
    verdict: dict[str, Any] = field(default_factory=dict)

    @property
    def failed_expectations(self) -> list[dict[str, Any]]:
        exps = self.verdict.get("expectations") or []
        return [e for e in exps if not e.get("satisfied")]

    @property
    def passed(self) -> bool:
        return (self.routing_ok
                and not self.grounding_violations
                and not self.failed_expectations
                and "error" not in self.verdict)


def run_attack(case: AttackCase, *, reference_year: int | None = None) -> AttackResult:
    ref = reference_year if reference_year is not None else solar_ganzhi_year(datetime.now())
    state = ConversationState(birth_info=ANCHOR_BIRTH, current_topic=case.current_topic)
    decision = route(case.message, state)

    routing_ok = decision.action in case.expected_actions
    if case.expected_topic is not None:
        routing_ok = routing_ok and decision.topic == case.expected_topic

    result = AttackResult(case=case, action=decision.action, topic=decision.topic,
                          routing_ok=routing_ok, reply="", reply_mode="none")

    # 路由挡下的（out_of_scope/smalltalk）走确定性模板，已知安全，不必 judge。
    if decision.action == "out_of_scope":
        result.reply, result.reply_mode = build_out_of_scope_reply()[0], "deterministic"
        return result
    if decision.action == "smalltalk":
        result.reply, result.reply_mode = build_smalltalk_reply()[0], "deterministic"
        return result
    if decision.action not in ("consult", "clarify"):
        return result  # ask_birth_info 等：状态齐全时出现即路由失败，上面已判

    # 漏进咨询管线的（或本就该咨询的），生成真实回复并 judge——看到实际伤害。
    tool_result = run_bazibase_tools(ANCHOR_BIRTH, reference_year=ref)
    parts: list[str] = []
    trace: dict[str, Any] | None = None
    for chunk, _state, gen_trace in stream_consultation_reply(
        decision.topic, tool_result,
        source_basis=_SOURCE_BASIS,
        clarify_previous=(decision.action == "clarify"),
        user_message=case.message,
        history=list(case.history),
        memory_notes=None,
        tone=None,
    ):
        if chunk:
            parts.append(chunk)
        if gen_trace is not None:
            trace = gen_trace

    result.reply = "".join(parts)
    result.reply_mode = "llm"
    result.grounding_violations = list((trace or {}).get("grounding_violations", []))

    if case.must or case.must_not:
        # 复用单轮 judge：把攻击轮包装成 EvalCase，多轮背景由 must/must_not 编码。
        shim = EvalCase(id=case.id, topic=decision.topic or case.current_topic,
                        question=case.message, birth=ANCHOR_BIRTH,
                        must=case.must, must_not=case.must_not)
        result.verdict = judge(RunResult(
            case=shim, reply=result.reply, facts=engine_facts(tool_result),
            grounding_violations=result.grounding_violations, reference_year=ref,
        ))
    return result


def _pick(argv: list[str]) -> list[AttackCase]:
    if not argv:
        return ATTACKS
    picked: list[AttackCase] = []
    for a in argv:
        if a in ATTACKS_BY_ID:
            picked.append(ATTACKS_BY_ID[a])
        elif a in CATEGORIES:
            picked.extend(c for c in ATTACKS if c.category == a)
        else:
            raise SystemExit(f"未知用例/类别：{a}\n可用类别：{', '.join(CATEGORIES)}\n"
                             f"可用 id：{', '.join(ATTACKS_BY_ID)}")
    return picked


def build_report(results: list[AttackResult]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# 带偏攻击评测报告\n\n生成时间:{now}\n用例数:{len(results)}\n"]

    lines.append("## 分类汇总\n")
    lines.append("| 类别 | 通过 | 失败 | 失败用例 |")
    lines.append("| --- | --- | --- | --- |")
    for cat in CATEGORIES:
        rs = [r for r in results if r.case.category == cat]
        if not rs:
            continue
        failed = [r for r in rs if not r.passed]
        ids = "、".join(r.case.id for r in failed) or "—"
        lines.append(f"| {cat} | {len(rs) - len(failed)} | {len(failed)} | {ids} |")
    lines.append("")

    lines.append("## 逐用例\n")
    for r in results:
        mark = "✅" if r.passed else "❌"
        lines.append(f"### {mark} `{r.case.id}` · {r.case.category}\n")
        lines.append(f"**攻击消息**:{r.case.message}\n")
        lines.append(f"**路由**:action=`{r.action}` topic=`{r.topic}` → "
                     f"{'符合预期' if r.routing_ok else f'不符({r.case.expected_actions} 之外)'}\n")
        if r.grounding_violations:
            lines.append(f"**grounding 违规**:{'；'.join(r.grounding_violations)}\n")
        ov = overall_score(r.verdict)
        if ov is not None:
            lines.append(f"**judge 总分**:{ov:.2f}\n")
        for e in r.failed_expectations:
            lines.append(f"- ❌（{e.get('kind')}）{e.get('text')} — {e.get('reason', '')}")
        if "error" in r.verdict:
            lines.append(f"- ⚠ judge 出错:{r.verdict['error']}")
        if r.case.note:
            lines.append(f"\n> {r.case.note}")
        if r.reply:
            lines.append(f"\n<details><summary>回复全文（{r.reply_mode}）</summary>\n\n"
                         f"{r.reply}\n\n</details>\n")
    return "\n".join(lines)


def write_report(content: str) -> Path:
    _REPORT_DIR.mkdir(exist_ok=True)
    path = _REPORT_DIR / f"attack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(content, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not is_configured():
        print("⚠ LLM 未配置（需要 DEEPSEEK_API_KEY 或 LLM_API_KEY）。攻击 eval 依赖真实模型，已退出。")
        return 1

    cases = _pick(argv)
    results: list[AttackResult] = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] ▶ {case.id} ({case.category}) …", flush=True)
        r = run_attack(case)
        status = "✅ 通过" if r.passed else "❌ 失败"
        detail = f"action={r.action}"
        if r.failed_expectations:
            detail += f" · 期望未满足 {len(r.failed_expectations)}"
        if r.grounding_violations:
            detail += f" · grounding 违规 {len(r.grounding_violations)}"
        print(f"        {status} · {detail}", flush=True)
        results.append(r)

    path = write_report(build_report(results))
    passed = sum(1 for r in results if r.passed)
    print(f"\n通过 {passed}/{len(results)}")
    print(f"✓ 报告已写入：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
