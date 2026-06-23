#!/usr/bin/env python3
"""
DeepSeek arbitration runner for bazibase.

这是 Layer 3 的集成验证代码——把 bazibase 确定性生成的仲裁 prompt
真正发给 DeepSeek，拿回结果用 parse_arbitration_response 解析，
验证「结构化 prompt + 强制置信度」是否真能产出可靠的仲裁判断。

bazibase 的设计原则是「库内不调 LLM」，所以这段代码在 examples/ 下，
是调用方（你）的胶水层，不是核心库的一部分。

用法
----
    # 单个命例
    export DEEPSEEK_API_KEY="sk-..."
    python examples/deepseek_runner.py single 1893-12-26 08:00 \\
        --lon 112.9 --gender male

    # 批量跑 sample_charts.json
    python examples/deepseek_runner.py batch examples/sample_charts.json

    # 只生成 prompt 不调用 LLM（dry-run，用于检查 prompt 质量）
    python examples/deepseek_runner.py single 1893-12-26 08:00 \\
        --lon 112.9 --gender male --dry-run

设计要点
--------
1. temperature=0.0  —— 尽可能确定性，与 bazibase 哲学一致
2. response_format=json_object  —— 强制 JSON 输出，降低解析失败率
3. 解析失败时自动重试一次（带「修正 JSON」提示）
4. 每个 case 的原始响应保留在 raw_response，方便审计
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any

# 确保能 import bazibase（从项目根目录运行或从 examples/ 运行都行）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from bazibase import cast_chart, diagnose  # noqa: E402
from bazibase.arbitration import (  # noqa: E402
    prepare_arbitration,
    parse_arbitration_response,
    attach_response,
    ArbitrationResult,
    ArbitrationPrompt,
    ArbitrationParseError,
    DEFAULT_CONFIDENCE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# DeepSeek API 配置
# ---------------------------------------------------------------------------

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "60"))
MAX_RETRIES = 1  # 解析失败时的重试次数


class DeepSeekAPIError(Exception):
    """DeepSeek API 调用失败。"""


def call_deepseek(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: str,
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.0,
    base_url: str = DEEPSEEK_BASE_URL,
    timeout: int = DEEPSEEK_TIMEOUT,
) -> str:
    """调用 DeepSeek chat completions API，返回 content 字符串。

    DeepSeek 的 API 与 OpenAI 完全兼容。使用 response_format=json_object
    强制 JSON 输出。temperature=0.0 保证最大确定性。
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise DeepSeekAPIError(
            f"DeepSeek API 返回 HTTP {e.code}: {err_body[:500]}"
        ) from e
    except urllib.error.URLError as e:
        raise DeepSeekAPIError(f"网络错误: {e.reason}") from e

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise DeepSeekAPIError(
            f"DeepSeek 响应结构异常，无法提取 content: {json.dumps(body, ensure_ascii=False)[:500]}"
        ) from e


# ---------------------------------------------------------------------------
# 单 case 仲裁（带重试）
# ---------------------------------------------------------------------------

def arbitrate_one_case(
    prompt: ArbitrationPrompt,
    api_key: str,
    *,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[str | None, str, Exception | None]:
    """对单个 case 调用 DeepSeek 并解析结果。

    Returns:
        (response_text, status_label, error)
        - response_text: LLM 原始返回（成功时），None（彻底失败时）
        - status_label: "OK" / "UNRESOLVED" / "PARSE_ERROR" / "API_ERROR"
        - error: 失败时的异常对象，成功时为 None
    """
    last_error: Exception | None = None
    last_raw: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        # 构造 user prompt（重试时加修正提示）
        actual_user_prompt = prompt.user_prompt
        if attempt > 0 and last_raw is not None:
            actual_user_prompt = (
                f"你上次的回复无法解析为合法 JSON，请修正。\n"
                f"上次回复片段: {last_raw[:200]}\n\n"
                f"请重新回答以下问题，必须输出严格 JSON：\n\n{prompt.user_prompt}"
            )

        try:
            raw = call_deepseek(
                system_prompt=prompt.system_prompt,
                user_prompt=actual_user_prompt,
                api_key=api_key,
            )
        except DeepSeekAPIError as e:
            last_error = e
            # API 错误不重试（通常是配额/网络问题，重试无益）
            return None, "API_ERROR", e

        last_raw = raw

        try:
            response = parse_arbitration_response(prompt.case, raw)
        except ArbitrationParseError as e:
            last_error = e
            continue  # 解析失败，重试

        # 解析成功
        status = "UNRESOLVED" if response.is_unresolved(threshold) else "OK"
        return raw, status, None

    # 所有重试都失败
    assert last_raw is not None
    return last_raw, "PARSE_ERROR", last_error


# ---------------------------------------------------------------------------
# 全流程：birth params -> ArbitrationResult with responses
# ---------------------------------------------------------------------------

def run_full_pipeline(
    birth_time: datetime,
    longitude: float,
    gender: str,
    *,
    api_key: str,
    tz_offset_hours: float = 8.0,
    apply_solar_time_correction: bool = True,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    verbose: bool = True,
) -> tuple[Any, Any, ArbitrationResult | None]:
    """跑通 cast_chart -> diagnose -> prepare_arbitration -> call DeepSeek 全流程。

    Returns:
        (chart, diagnosis, arbitration_result_or_none)
        arbitration_result 为 None 表示该命例无仲裁 case。
    """
    chart = cast_chart(
        birth_time=birth_time,
        longitude=longitude,
        gender=gender,
        tz_offset_hours=tz_offset_hours,
        apply_solar_time_correction=apply_solar_time_correction,
    )
    diag = diagnose(chart)

    if verbose:
        print(f"\n{'='*60}")
        print(f"排盘: {chart.summary()}")
        print(f"诊断: {diag.summary()}")

    result = prepare_arbitration(diag)

    if not result.has_cases():
        if verbose:
            print("无仲裁 case（确定性规则已覆盖全部判断）。")
        return chart, diag, result

    if verbose:
        print(f"检测到 {len(result.cases)} 个仲裁 case：")
        for c in result.cases:
            print(f"  [{c.case_id}] {c.category}: {c.title}")

    # 逐个 case 调用 DeepSeek
    for prompt in result.prompts:
        case = prompt.case
        if verbose:
            print(f"\n--- {case.case_id} ({case.category}) ---")

        raw, status, err = arbitrate_one_case(prompt, api_key, threshold=threshold)

        if status == "API_ERROR":
            if verbose:
                print(f"  ❌ API 错误: {err}")
            continue  # 跳过，不 attach

        if status == "PARSE_ERROR":
            if verbose:
                print(f"  ❌ 解析失败（重试 {MAX_RETRIES} 次后仍不合法）")
                print(f"     原始返回: {raw[:300] if raw else 'N/A'}")
            continue

        # 成功解析
        try:
            response = parse_arbitration_response(case, raw)
        except ArbitrationParseError:
            continue  # 理论上不会到这

        result = attach_response(result, case.case_id, response)

        if verbose:
            conf_bar = _confidence_bar(response.confidence)
            print(f"  {status}  置信度={response.confidence:.2f} {conf_bar}")
            print(f"  决定: {response.decision}")
            print(f"  推理: {response.reasoning}")
            if response.cited_rules:
                print(f"  引用规则: {', '.join(response.cited_rules)}")

    return chart, diag, result


def _confidence_bar(c: float) -> str:
    """0.0-1.0 置信度的可视化条。"""
    filled = int(c * 10)
    return "█" * filled + "░" * (10 - filled)


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------

def print_summary_report(
    chart_label: str,
    result: ArbitrationResult | None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> dict:
    """打印单个命例的仲裁汇总，返回结构化统计。"""
    stats = {
        "label": chart_label,
        "total_cases": 0,
        "resolved": 0,
        "unresolved": 0,
        "errors": 0,
        "by_category": {},
    }

    if result is None or not result.has_cases():
        print(f"\n{'='*60}")
        print(f"[{chart_label}] 无仲裁 case")
        return stats

    stats["total_cases"] = len(result.cases)

    for case in result.cases:
        cat = case.category
        stats["by_category"].setdefault(cat, {"total": 0, "resolved": 0, "unresolved": 0})
        stats["by_category"][cat]["total"] += 1

        resp = result.responses.get(case.case_id)
        if resp is None:
            stats["errors"] += 1
            continue

        if resp.is_unresolved(threshold):
            stats["unresolved"] += 1
            stats["by_category"][cat]["unresolved"] += 1
        else:
            stats["resolved"] += 1
            stats["by_category"][cat]["resolved"] += 1

    print(f"\n{'='*60}")
    print(f"[{chart_label}] 仲裁汇总")
    print(f"  总 case 数: {stats['total_cases']}")
    print(f"  已解决:    {stats['resolved']}")
    print(f"  未解决:    {stats['unresolved']} (无法判定或置信度 < {threshold})")
    print(f"  错误:      {stats['errors']}")

    if stats["by_category"]:
        print(f"  按类别:")
        for cat, s in stats["by_category"].items():
            print(f"    {cat:20s} {s['resolved']}/{s['total']} 解决")

    return stats


# ---------------------------------------------------------------------------
# CLI 命令
# ---------------------------------------------------------------------------

def _parse_datetime(date_str: str, time_str: str) -> datetime:
    combined = f"{date_str} {time_str}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期时间: {combined!r}")


def cmd_single(args: argparse.Namespace) -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    # dry-run 模式：只生成 prompt，不调 LLM
    if args.dry_run:
        return _cmd_single_dry_run(args)

    if not api_key:
        print("错误: 未设置 DEEPSEEK_API_KEY 环境变量", file=sys.stderr)
        return 2

    try:
        birth_time = _parse_datetime(args.date, args.time)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2

    _, diag, result = run_full_pipeline(
        birth_time=birth_time,
        longitude=args.lon,
        gender=args.gender,
        api_key=api_key,
        tz_offset_hours=args.tz,
        apply_solar_time_correction=not args.no_solar,
        threshold=args.threshold,
    )

    label = args.label or f"{args.date} {args.time}"
    print_summary_report(label, result, args.threshold)

    if args.json:
        out = {
            "label": label,
            "diagnosis": diag.to_dict(),
            "arbitration": _result_to_dict(result),
        }
        print("\n" + json.dumps(out, ensure_ascii=False, indent=2))

    return 0


def _cmd_single_dry_run(args: argparse.Namespace) -> int:
    """只生成 prompt，打印出来供人工检查，不调 LLM。"""
    try:
        birth_time = _parse_datetime(args.date, args.time)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2

    chart = cast_chart(
        birth_time=birth_time,
        longitude=args.lon,
        gender=args.gender,
        tz_offset_hours=args.tz,
        apply_solar_time_correction=not args.no_solar,
    )
    diag = diagnose(chart)
    result = prepare_arbitration(diag)

    print(f"排盘: {chart.summary()}")
    print(f"诊断: {diag.summary()}")

    if not result.has_cases():
        print("\n无仲裁 case。")
        return 0

    print(f"\n检测到 {len(result.cases)} 个仲裁 case，prompt 如下：\n")
    for i, prompt in enumerate(result.prompts):
        print(f"{'#' * 60}")
        print(f"# Case {i+1}/{len(result.prompts)}: [{prompt.case.case_id}] {prompt.case.category}")
        print(f"# {prompt.case.title}")
        print(f"{'#' * 60}")
        print(f"\n--- SYSTEM PROMPT ---\n{prompt.system_prompt}")
        print(f"\n--- USER PROMPT ---\n{prompt.user_prompt}")
        print(f"\n--- EXPECTED SCHEMA ---\n{json.dumps(prompt.expected_schema, ensure_ascii=False, indent=2)}")
        print()

    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key and not args.dry_run:
        print("错误: 未设置 DEEPSEEK_API_KEY 环境变量", file=sys.stderr)
        return 2

    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)

    charts = data.get("charts", [])
    if not charts:
        print("错误: 文件中无 charts", file=sys.stderr)
        return 2

    all_stats = []
    for i, item in enumerate(charts):
        label = item.get("label", item.get("id", f"chart-{i+1}"))
        try:
            birth_time = _parse_datetime(item["date"], item["time"])
        except (ValueError, KeyError) as e:
            print(f"\n[{label}] 跳过：日期解析失败 ({e})")
            continue

        if args.dry_run:
            chart = cast_chart(
                birth_time=birth_time,
                longitude=item["lon"],
                gender=item["gender"],
                tz_offset_hours=item.get("tz", 8.0),
            )
            diag = diagnose(chart)
            result = prepare_arbitration(diag)
            n_cases = len(result.cases) if result.has_cases() else 0
            print(f"[{label}] {chart.summary()} -> {n_cases} 个仲裁 case")
            all_stats.append({"label": label, "total_cases": n_cases})
            continue

        _, _, result = run_full_pipeline(
            birth_time=birth_time,
            longitude=item["lon"],
            gender=item["gender"],
            api_key=api_key,
            tz_offset_hours=item.get("tz", 8.0),
            threshold=args.threshold,
            verbose=True,
        )
        stats = print_summary_report(label, result, args.threshold)
        all_stats.append(stats)

        # 批量时每个 case 之间稍微停顿，避免 rate limit
        if i < len(charts) - 1:
            time.sleep(1)

    # 总汇总
    print(f"\n{'='*60}")
    print("批量汇总")
    print(f"{'='*60}")
    total = sum(s.get("total_cases", 0) for s in all_stats)
    print(f"命例数:   {len(all_stats)}")
    print(f"总 case:  {total}")

    if args.dry_run:
        # dry-run 没有 resolved/unresolved，只报 case 数
        per_label = {s["label"]: s.get("total_cases", 0) for s in all_stats}
        for lbl, cnt in per_label.items():
            print(f"  {lbl}: {cnt}")
    else:
        resolved = sum(s.get("resolved", 0) for s in all_stats)
        unresolved = sum(s.get("unresolved", 0) for s in all_stats)
        errors = sum(s.get("errors", 0) for s in all_stats)
        print(f"已解决:   {resolved}")
        print(f"未解决:   {unresolved}")
        print(f"错误:     {errors}")
        if total > 0:
            print(f"解决率:   {resolved/total:.1%}")

    if args.json:
        print("\n" + json.dumps(all_stats, ensure_ascii=False, indent=2))

    return 0


def _result_to_dict(result: ArbitrationResult | None) -> dict:
    if result is None:
        return {}
    return {
        "cases": [
            {
                "case_id": c.case_id,
                "category": c.category,
                "title": c.title,
            }
            for c in result.cases
        ],
        "responses": {
            cid: {
                "decision": r.decision,
                "reasoning": r.reasoning,
                "confidence": r.confidence,
                "cited_rules": list(r.cited_rules),
            }
            for cid, r in result.responses.items()
        },
    }


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deepseek_runner",
        description="bazibase Layer 3 仲裁验证——对接 DeepSeek 跑通全流程",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # single
    s = sub.add_parser("single", help="单个命例")
    s.add_argument("date", help="YYYY-MM-DD")
    s.add_argument("time", help="HH:MM 或 HH:MM:SS")
    s.add_argument("--lon", type=float, required=True, help="出生地经度")
    s.add_argument("--gender", choices=["male", "female"], required=True)
    s.add_argument("--tz", type=float, default=8.0, help="时区，默认 8.0")
    s.add_argument("--no-solar", action="store_true", help="不做真太阳时修正")
    s.add_argument("--label", default=None, help="命例标签（用于报告）")
    s.add_argument("--threshold", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD,
                   help=f"置信度阈值，默认 {DEFAULT_CONFIDENCE_THRESHOLD}")
    s.add_argument("--dry-run", action="store_true", help="只生成 prompt，不调 LLM")
    s.add_argument("--json", action="store_true", help="输出 JSON")

    # batch
    b = sub.add_parser("batch", help="批量跑 JSON 文件中的命例")
    b.add_argument("file", help="JSON 文件路径")
    b.add_argument("--threshold", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD,
                   help=f"置信度阈值，默认 {DEFAULT_CONFIDENCE_THRESHOLD}")
    b.add_argument("--dry-run", action="store_true", help="只统计 case 数，不调 LLM")
    b.add_argument("--json", action="store_true", help="输出 JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "single":
        return cmd_single(args)
    elif args.command == "batch":
        return cmd_batch(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
