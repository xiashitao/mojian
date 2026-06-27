"""Render eval rows into a comparable markdown report."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from web.backend.eval.judge import DIMENSIONS, overall_score
from web.backend.eval.runner import RunResult

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def _fmt(x: float | None) -> str:
    return f"{x:.2f}" if isinstance(x, (int, float)) else "—"


def build_report(rows: list[dict[str, Any]]) -> str:
    """rows: [{"result": RunResult, "verdict": dict}]."""
    out: list[str] = ["# Kairos 回答质量评测报告", "",
                      f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
                      f"用例数：{len(rows)}", ""]

    # ── 汇总 ──
    dim_vals: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    overalls: list[float] = []
    total_grounding = 0
    failed_expectations = 0
    for row in rows:
        verdict = row["verdict"]
        scores = verdict.get("scores") if isinstance(verdict, dict) else None
        if isinstance(scores, dict):
            for d in DIMENSIONS:
                if isinstance(v := scores.get(d), (int, float)):
                    dim_vals[d].append(float(v))
        if (ov := overall_score(verdict)) is not None:
            overalls.append(ov)
        total_grounding += len(row["result"].grounding_violations)
        for e in (verdict.get("expectations") or []) if isinstance(verdict, dict) else []:
            if not e.get("satisfied"):
                failed_expectations += 1

    out.append("## 汇总")
    out.append("")
    out.append("| 指标 | 值 |")
    out.append("| --- | --- |")
    out.append(f"| 总均分（5 维平均） | {_fmt(sum(overalls)/len(overalls) if overalls else None)} |")
    for d in DIMENSIONS:
        avg = sum(dim_vals[d]) / len(dim_vals[d]) if dim_vals[d] else None
        out.append(f"| {d} 均分 | {_fmt(avg)} |")
    out.append(f"| grounding 违规总数 | {total_grounding} |")
    out.append(f"| 未满足的期望条数 | {failed_expectations} |")
    out.append("")

    # ── 逐 case ──
    out.append("## 逐用例")
    for row in rows:
        result: RunResult = row["result"]
        verdict: dict[str, Any] = row["verdict"]
        case = result.case
        out.append("")
        out.append(f"### `{case.id}` · {case.topic} — 总分 {_fmt(overall_score(verdict))}")
        out.append("")
        out.append(f"**问题**：{case.question}")
        out.append("")
        if "error" in verdict:
            out.append(f"> ⚠ 评分失败：{verdict['error']}")
        else:
            scores = verdict.get("scores") or {}
            score_line = " · ".join(f"{d} {scores.get(d, '—')}" for d in DIMENSIONS)
            out.append(f"**评分**：{score_line}")
            out.append("")
            out.append(f"**总评**：{verdict.get('summary', '')}")
            exps = verdict.get("expectations") or []
            if exps:
                out.append("")
                out.append("**期望核对**：")
                for e in exps:
                    mark = "✅" if e.get("satisfied") else "❌"
                    out.append(f"- {mark}（{e.get('kind')}）{e.get('text')} — {e.get('reason', '')}")
            issues = verdict.get("issues") or []
            if issues:
                out.append("")
                out.append("**问题点**：")
                out.extend(f"- {i}" for i in issues)
        if result.grounding_violations:
            out.append("")
            out.append("**grounding 违规**：" + "；".join(result.grounding_violations))
        # 引擎事实 + 回答，供人工复核
        out.append("")
        out.append("<details><summary>引擎事实 / 回答全文</summary>")
        out.append("")
        out.append("```json")
        import json
        out.append(json.dumps(result.facts, ensure_ascii=False, indent=2))
        out.append("```")
        out.append("")
        out.append(result.reply)
        out.append("")
        out.append("</details>")
    return "\n".join(out)


def write_report(markdown: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"eval_{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
