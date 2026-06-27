"""CLI entry — run cases through the pipeline, judge them, write a report.

    PYTHONPATH=. python -m web.backend.eval.run                  # all cases
    PYTHONPATH=. python -m web.backend.eval.run tongling-1997    # one or more ids
"""
from __future__ import annotations

import sys

from web.backend.services.llm import is_configured
from web.backend.eval.cases import CASES, CASES_BY_ID
from web.backend.eval.judge import judge, overall_score
from web.backend.eval.report import build_report, write_report
from web.backend.eval.runner import run_case


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not is_configured():
        print("⚠ LLM 未配置（需要 DEEPSEEK_API_KEY 或 LLM_API_KEY）。eval 依赖真实模型，已退出。")
        return 1

    if argv:
        unknown = [a for a in argv if a not in CASES_BY_ID]
        if unknown:
            print(f"未知用例：{', '.join(unknown)}\n可用：{', '.join(CASES_BY_ID)}")
            return 1
        cases = [CASES_BY_ID[a] for a in argv]
    else:
        cases = CASES

    rows = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] ▶ {case.id} …", flush=True)
        result = run_case(case)
        verdict = judge(result)
        ov = overall_score(verdict)
        flag = "✗ 评分失败" if "error" in verdict else f"总分 {ov:.2f}" if ov is not None else "无分"
        print(f"        {flag} · grounding 违规 {len(result.grounding_violations)}", flush=True)
        rows.append({"result": result, "verdict": verdict})

    path = write_report(build_report(rows))
    print(f"\n✓ 报告已写入：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
