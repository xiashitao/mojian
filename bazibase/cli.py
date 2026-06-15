"""
bazibase.cli
============

Command-line interface for bazibase.

Usage
-----
    bazibase diagnose <date> <time> --lon <float> --gender <male|female> [options]

Output modes (mutually exclusive where marked):

    (default)      one-line summary
    --explain      teaching mode: full reasoning chain with rule citations
    --json         structured JSON (chart + diagnosis)
    --chart-only   limit to Layer 1 (no Layer 2 diagnosis)
    --arbitrate    output LLM arbitration prompts as a JSON array

Examples
--------
    # Default: one-line summary
    bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male

    # Teaching mode
    bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --explain

    # JSON output
    bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --json

    # Arbitration prompts (pipe to external LLM)
    bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --arbitrate
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from .chart import cast_chart
from .engine import diagnose
from .arbitration import prepare_arbitration


# ---------------------------------------------------------------------------
# Date/time parsing
# ---------------------------------------------------------------------------

def _parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse '1893-12-26' + '08:00' into a naive datetime.

    Accepts HH:MM or HH:MM:SS for the time component.
    """
    combined = f"{date_str} {time_str}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"无法解析日期时间: {combined!r}\n"
        "期望格式: YYYY-MM-DD HH:MM  或  YYYY-MM-DD HH:MM:SS"
    )


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bazibase",
        description="八字命理确定性排盘与诊断引擎 (bazibase)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- diagnose ---
    d = sub.add_parser(
        "diagnose",
        help="排盘并诊断",
        description="根据出生时间排八字命盘，给出确定性诊断。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male\n"
            "  bazibase diagnose 2000-06-15 12:00 --lon 116.4 --gender female --json\n"
            "  bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --arbitrate"
        ),
    )
    d.add_argument("date", help="出生日期，格式 YYYY-MM-DD，如 1893-12-26")
    d.add_argument("time", help="出生时间，格式 HH:MM 或 HH:MM:SS，如 08:00")
    d.add_argument("--lon", type=float, required=True,
                   help="出生地经度（东经为正），如 北京 116.4")
    d.add_argument("--gender", choices=["male", "female"], required=True,
                   help="性别")
    d.add_argument("--tz", type=float, default=8.0,
                   help="时区偏移（小时），默认 8.0（北京时间）")
    d.add_argument("--no-solar", action="store_true",
                   help="不做真太阳时修正（仅在已知输入为真太阳时时使用）")
    d.add_argument("--luck", type=int, default=8,
                   help="大运数量，默认 8（约 80 年）")

    # Output format (explain vs json are mutually exclusive text/structured modes)
    fmt = d.add_mutually_exclusive_group()
    fmt.add_argument("--explain", action="store_true",
                     help="教学模式：输出完整推理链与规则原文")
    fmt.add_argument("--json", action="store_true",
                     help="JSON 结构化输出")

    # Scope modifier
    d.add_argument("--chart-only", action="store_true",
                   help="仅排盘（Layer 1），不做 Layer 2 诊断")

    # Arbitration mode (independent — always emits JSON array)
    d.add_argument("--arbitrate", action="store_true",
                   help="输出 LLM 仲裁 prompts（JSON 数组），可管道给外部 LLM")

    return parser


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _format_arbitration_output(result) -> str:
    """Format an ArbitrationResult as a JSON array of prompt bundles."""
    output = [
        {
            "case_id": p.case.case_id,
            "category": p.case.category,
            "title": p.case.title,
            "description": p.case.description,
            "evidence": p.case.evidence,
            "relevant_rules": list(p.case.relevant_rules),
            "options": list(p.case.options),
            "system_prompt": p.system_prompt,
            "user_prompt": p.user_prompt,
            "expected_schema": p.expected_schema,
        }
        for p in result.prompts
    ]
    return json.dumps(output, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _run_diagnose(args: argparse.Namespace) -> int:
    """Execute the `diagnose` subcommand. Returns process exit code."""
    # Parse date/time
    try:
        birth_time = _parse_datetime(args.date, args.time)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2

    # Cast chart (Layer 1)
    try:
        chart = cast_chart(
            birth_time=birth_time,
            longitude=args.lon,
            gender=args.gender,
            tz_offset_hours=args.tz,
            apply_solar_time_correction=not args.no_solar,
            luck_pillar_count=args.luck,
        )
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2

    # --- Priority 1: --arbitrate (always JSON array) ---
    if args.arbitrate:
        diag = diagnose(chart)
        result = prepare_arbitration(diag)
        print(_format_arbitration_output(result))
        return 0

    # --- Priority 2: --chart-only (Layer 1 scope) ---
    if args.chart_only:
        if args.json:
            print(json.dumps(chart.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(chart.summary())
        return 0

    # --- Priority 3: full diagnosis ---
    diag = diagnose(chart)

    if args.explain:
        print(diag.explain())
    elif args.json:
        out = {
            "chart": chart.to_dict(),
            "diagnosis": diag.to_dict(),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        # Default: one-line summary
        print(diag.summary())

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "diagnose":
        return _run_diagnose(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
