"""
bazibase.engine
===============

Top-level entry point for Layer 2.

Takes a Chart (from Layer 1) and produces a Diagnosis by applying the
rule library:

    1. Determine 用神 (deterministic algorithm)
    2. Determine 格局 (mapping from 用神 十神)
    3. Identify 相神 and 忌神 (v0.2.2)
    4. Assess 格局成败 (v0.2.2)
    5. Detect 刑冲合化 (v0.2.3)

Future versions will add:

    6. LLM arbitration for rule conflicts (v0.3.0)
"""
from __future__ import annotations

from .chart import Chart
from .diagnosis import Diagnosis
from .rules import (
    determine_yong_shen,
    determine_ge_ju,
    identify_xiang_ji,
    assess_cheng_bai,
    detect_interactions,
    RuleCitation,
)


def diagnose(chart: Chart) -> Diagnosis:
    """
    Apply Layer 2 rules to a Chart and return a Diagnosis.

    Args:
        chart: A Chart from `bazibase.cast_chart`.

    Returns:
        Diagnosis with 用神, 格局, 相神/忌神, 成败, and full citation chain.

    Example:
        >>> from datetime import datetime
        >>> from bazibase import cast_chart
        >>> from bazibase.engine import diagnose
        >>> c = cast_chart(datetime(1893,12,26,8,0), 112.9, "male")
        >>> d = diagnose(c)
        >>> d.summary()
        '癸巳年 甲子月 丁酉日 甲辰时 | 日主丁(身弱) | 逆运 6岁起运 | 用神癸(七杀) | 七杀格 | 救应'
        >>> print(d.explain())   # full teaching-mode explanation
    """
    ys = determine_yong_shen(chart)
    gj = determine_ge_ju(chart, ys)
    xs = identify_xiang_ji(chart, ys)
    cb = assess_cheng_bai(chart, ys, gj, xs)
    ia = detect_interactions(chart)

    # Flatten all citations in order.
    all_citations: list[RuleCitation] = []
    all_citations.extend(ys.citations)
    all_citations.extend(gj.citations)
    all_citations.extend(xs.citations)
    all_citations.extend(cb.citations)
    all_citations.extend(ia.citations)

    return Diagnosis(
        chart_summary=chart.summary(),
        day_master=chart.day_master,
        yong_shen=ys,
        ge_ju=gj,
        xiang_shen=xs,
        cheng_bai=cb,
        interactions=ia,
        all_citations=tuple(all_citations),
    )


__all__ = ["diagnose"]
