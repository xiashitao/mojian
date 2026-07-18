"""观测查询 CLI:调用链树 / 成本报表 / 最近 run 列表 / 用户记忆视图。

用法(repo 根目录):
    PYTHONPATH=. python -m web.backend.obs_cli show <run_id|analysis_id>
    PYTHONPATH=. python -m web.backend.obs_cli costs [--days 7]
    PYTHONPATH=. python -m web.backend.obs_cli recent [--limit 20]
    PYTHONPATH=. python -m web.backend.obs_cli memory <memory_key> [--subject self]

只读:查的都是已落库的数据,不碰管线。
"""
from __future__ import annotations

import argparse
import json
import sys

from .agent import memory as memory_store
from .agent import repository
from .agent.context import render_profile


def _fmt_tokens(n) -> str:
    if not n:
        return ""
    return f"{n / 1000:.1f}k tok" if n >= 1000 else f"{n} tok"


def _fmt_cost(cost) -> str:
    return f"¥{cost:.4f}" if cost is not None else ""


def _step_line(trace: dict) -> str:
    """一步 trace 的展示行:类型 + 关键指标(延迟/token/成本/错误)。"""
    out = trace.get("output_json") or {}
    parts = [trace["step_type"]]
    name = out.get("name") if isinstance(out, dict) else None
    if name:
        parts.append(name)
    if isinstance(out, dict):
        if out.get("latency_ms"):
            parts.append(f"{out['latency_ms']}ms")
        tok = _fmt_tokens(out.get("total_tokens"))
        if tok:
            parts.append(tok)
        if out.get("cost") is not None:
            parts.append(_fmt_cost(out["cost"]))
        if out.get("ok") is False:
            parts.append(f"FAIL: {str(out.get('error', ''))[:60]}")
    return " · ".join(parts)


def cmd_show(ref: str) -> int:
    data = repository.get_run_with_traces(ref)
    if not data:
        print(f"未找到 run:{ref}", file=sys.stderr)
        return 1
    run, traces = data["run"], data["traces"]

    # 只统计外部调用步骤(llm_call/tool_call…),管线步骤的 output 可能
    # 转录了同一份 token 数,计入会重复。
    call_outputs = [
        t["output_json"] for t in traces
        if t["step_type"].endswith("_call") and isinstance(t.get("output_json"), dict)
    ]
    total_tokens = sum(o.get("total_tokens") or 0 for o in call_outputs)
    total_cost = sum(o.get("cost") or 0 for o in call_outputs)
    head = [
        f"run {run['id']}",
        f"status={run['status']}",
        f"intent={run.get('intent') or '-'}",
        f"topic={run.get('topic') or '-'}",
        f"{run.get('latency_ms') or 0}ms",
    ]
    if total_tokens:
        head.append(_fmt_tokens(total_tokens))
    if total_cost:
        head.append(_fmt_cost(total_cost))
    print(" · ".join(head))
    if run.get("error"):
        print(f"  error: {run['error']}")

    for i, trace in enumerate(traces):
        branch = "└──" if i == len(traces) - 1 else "├──"
        print(f"{branch} {_step_line(trace)}")
        if trace.get("summary"):
            pad = "    " if i == len(traces) - 1 else "│   "
            print(f"{pad}{trace['summary']}")
    return 0


def cmd_costs(days: int) -> int:
    report = repository.cost_summary(days=days)
    print(f"== 近 {days} 天成本(元;NULL 定价的 run 不计入 cost)==")
    print(f"{'日期':<12}{'runs':>6}{'LLM调用':>8}{'tokens':>12}{'成本':>10}")
    for row in report["by_day"]:
        print(f"{row['day']:<12}{row['runs']:>6}{row['llm_calls'] or 0:>8}"
              f"{row['total_tokens'] or 0:>12}"
              f"{('¥%.4f' % row['cost']) if row['cost'] is not None else '-':>10}")
    if not report["by_day"]:
        print("(无数据)")
    print()
    print("== 按模型 ==")
    for row in report["by_model"]:
        print(f"{row['model']:<24}calls={row['calls'] or 0:<6}"
              f"in={row['prompt_tokens'] or 0:<10}out={row['completion_tokens'] or 0:<10}"
              f"cost={('¥%.4f' % row['cost']) if row['cost'] is not None else '-'}")
    if not report["by_model"]:
        print("(无数据)")
    return 0


def cmd_recent(limit: int) -> int:
    rows = repository.recent_runs(limit=limit)
    for r in rows:
        line = [
            r["started_at"], r["run_id"],
            r["status"],
            f"{r.get('latency_ms') or 0}ms",
        ]
        if r.get("total_tokens"):
            line.append(_fmt_tokens(r["total_tokens"]))
        if r.get("cost") is not None:
            line.append(_fmt_cost(r["cost"]))
        if r.get("error"):
            line.append(f"error: {str(r['error'])[:50]}")
        print(" · ".join(line))
    if not rows:
        print("(无数据)")
    return 0


def cmd_conv(conversation_id: str) -> int:
    """一段会话的全部轮次:每轮的用户问题 + 完整调用链树(模型/工具/记忆)。"""
    runs = repository.get_conversation_runs(conversation_id)
    if not runs:
        print(f"未找到会话或会话没有 run:{conversation_id}", file=sys.stderr)
        return 1
    for i, r in enumerate(runs, 1):
        print(f"━━ 第 {i}/{len(runs)} 轮 · {r.get('started_at', '')} "
              f"· 问:{r.get('user_message') or '(空)'}")
        cmd_show(r["analysis_id"])
        print()
    return 0


def cmd_feedback(days: int) -> int:
    """近期用户反馈:差评在前;每条带 analysis_id,拿去 `show` 即达该轮 trace。"""
    rows = repository.list_feedback(days=days)
    if not rows:
        print(f"近 {days} 天没有用户反馈")
        return 0
    rows.sort(key=lambda r: (r.get("feedback") != "dislike",))  # 差评优先
    for r in rows:
        mark = "👎" if r.get("feedback") == "dislike" else "👍"
        print(f"{mark} {r.get('feedback_at', '')} · {r.get('analysis_id')}"
              f" · [{r.get('topic') or '-'}]")
        if r.get("user_message"):
            print(f"   问:{r['user_message']}")
        if r.get("reply_excerpt"):
            print(f"   答:{r['reply_excerpt']}…")
        if r.get("comment"):
            print(f"   💬 用户评论:{r['comment']}")
        print()
    return 0


def cmd_memory(memory_key: str, subject: str | None) -> int:
    """一个用户的记忆全景:主体 → 生辰 / 画像 / 笔记(结论 + agent 自主记忆)。"""
    subjects = memory_store.list_subjects(memory_key)
    if not subjects:
        print(f"该用户没有任何记忆:{memory_key}")
        return 1
    targets = [subject] if subject else subjects
    for subj in targets:
        print(f"== 主体:{subj} ==")
        birth = memory_store.get_birth_info(memory_key, subj)  # type: ignore[arg-type]
        if birth:
            gender = {"male": "男", "female": "女"}.get(birth.gender or "", "")
            print(f"生辰:{birth.birth_date} {birth.birth_time or ''} "
                  f"{birth.birth_place or ''} {gender}".rstrip())
        else:
            print("生辰:(未记录)")
        profile = memory_store.get_profile(memory_key, subj)  # type: ignore[arg-type]
        profile_text = render_profile(profile)
        print(f"画像:{profile_text}" if profile_text else "画像:(空)")
        notes = memory_store.recent_notes(memory_key, subj, limit=20)  # type: ignore[arg-type]
        print(f"笔记({len(notes)} 条,新→旧):")
        for n in notes:
            head = f"  [{n.get('topic') or '-'}] {n.get('created_at', '')}"
            print(head)
            if (n.get("conclusion") or "").strip():
                print(f"    结论:{n['conclusion']}")
            if (n.get("memory_text") or "").strip():
                print(f"    记忆:{n['memory_text']}")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="obs_cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_show = sub.add_parser("show", help="一轮 run 的调用链树")
    p_show.add_argument("ref", help="run_id 或 analysis_id")

    p_costs = sub.add_parser("costs", help="成本报表(按天/按模型)")
    p_costs.add_argument("--days", type=int, default=7)

    p_recent = sub.add_parser("recent", help="最近 N 轮 run 概要")
    p_recent.add_argument("--limit", type=int, default=20)

    p_memory = sub.add_parser("memory", help="一个用户的记忆全景")
    p_memory.add_argument("memory_key")
    p_memory.add_argument("--subject", default=None)

    p_conv = sub.add_parser("conv", help="一段会话的全部轮次调用链")
    p_conv.add_argument("conversation_id")

    p_fb = sub.add_parser("feedback", help="近期用户反馈(差评优先)")
    p_fb.add_argument("--days", type=int, default=30)

    args = parser.parse_args(argv)
    if args.command == "show":
        return cmd_show(args.ref)
    if args.command == "costs":
        return cmd_costs(args.days)
    if args.command == "memory":
        return cmd_memory(args.memory_key, args.subject)
    if args.command == "conv":
        return cmd_conv(args.conversation_id)
    if args.command == "feedback":
        return cmd_feedback(args.days)
    return cmd_recent(args.limit)


if __name__ == "__main__":
    sys.exit(main())
