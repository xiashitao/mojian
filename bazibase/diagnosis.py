"""
bazibase.diagnosis
==================

Diagnosis output structure for Layer 2.

A Diagnosis is the structured output of applying 子平派 rules to a
Chart. It contains:

    - 用神 (yong-shen) — the central "useful god" of the chart
    - 格局 (ge-ju) — the named pattern
    - 相神/忌神 (xiang-shen / ji-shen) — supporters and attackers of 用神
    - 格局成败 (cheng-bai) — whether the pattern actually holds
    - All rule citations explaining each conclusion
    - Plain-language summary
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Optional

from .chart import Chart
from .rules import (
    YongShenResult,
    GeJuResult,
    XiangShenResult,
    ChengBaiResult,
    InteractionResult,
    RuleCitation,
    get_rule,
)


@dataclass(frozen=True)
class Diagnosis:
    """
    Structured output of Layer 2 — a diagnosis of a Ba Zi chart.

    Immutable and fully traceable: every conclusion cites one or more
    rules from 《子平真诠》.
    """
    chart_summary: str              # the Layer 1 summary line
    day_master: str
    yong_shen: YongShenResult
    ge_ju: GeJuResult
    xiang_shen: XiangShenResult
    cheng_bai: ChengBaiResult
    interactions: InteractionResult
    all_citations: tuple[RuleCitation, ...]

    def summary(self) -> str:
        """One-line summary of the diagnosis."""
        ys_str = (
            f"用神{self.yong_shen.stem}({self.yong_shen.ten_god})"
            if self.yong_shen.stem
            else "用神未定"
        )
        gj_str = self.ge_ju.name
        cb_str = f" | {self.cheng_bai.verdict}" if self.cheng_bai else ""
        unresolved_flag = (
            " [需进一步分析]"
            if (self.yong_shen.unresolved or self.ge_ju.unresolved)
            else ""
        )
        return f"{self.chart_summary} | {ys_str} | {gj_str}{cb_str}{unresolved_flag}"

    def to_dict(self) -> dict:
        """Serialise to a JSON-friendly dict."""
        return {
            "chart_summary": self.chart_summary,
            "day_master": self.day_master,
            "yong_shen": {
                "stem": self.yong_shen.stem,
                "ten_god": self.yong_shen.ten_god,
                "source_rule_id": self.yong_shen.source_rule_id,
                "is_bi_jie": self.yong_shen.is_bi_jie,
                "unresolved": self.yong_shen.unresolved,
                "alternative_source": self.yong_shen.alternative_source,
                "transparent_stems": [
                    {
                        "stem": t.hidden_stem,
                        "role": t.role,
                        "transparent_at": t.transparent_at,
                    }
                    for t in self.yong_shen.transparent_stems
                ],
                "citations": [self._citation_to_dict(c) for c in self.yong_shen.citations],
            },
            "ge_ju": {
                "name": self.ge_ju.name,
                "alias": self.ge_ju.alias,
                "category": self.ge_ju.category,
                "source_rule_id": self.ge_ju.source_rule_id,
                "unresolved": self.ge_ju.unresolved,
                "citations": [self._citation_to_dict(c) for c in self.ge_ju.citations],
            },
            "xiang_shen": {
                "xiang_shen": [
                    {
                        "position": o.position,
                        "location": o.location,
                        "stem": o.stem,
                        "ten_god": o.ten_god,
                    }
                    for o in self.xiang_shen.xiang_shen
                ],
                "ji_shen": [
                    {
                        "position": o.position,
                        "location": o.location,
                        "stem": o.stem,
                        "ten_god": o.ten_god,
                    }
                    for o in self.xiang_shen.ji_shen
                ],
                "notes": list(self.xiang_shen.notes),
                "citations": [self._citation_to_dict(c) for c in self.xiang_shen.citations],
            },
            "cheng_bai": {
                "verdict": self.cheng_bai.verdict,
                "source_rule_id": self.cheng_bai.source_rule_id,
                "rescue_gods": [
                    {
                        "position": g.position,
                        "location": g.location,
                        "stem": g.stem,
                        "ten_god": g.ten_god,
                    }
                    for g in self.cheng_bai.rescue_gods
                ],
                "unresolved": self.cheng_bai.unresolved,
                "citations": [self._citation_to_dict(c) for c in self.cheng_bai.citations],
            },
            "interactions": {
                "gan_he": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.gan_he
                ],
                "san_he": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.san_he
                ],
                "ban_he": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.ban_he
                ],
                "san_hui": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.san_hui
                ],
                "ban_hui": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.ban_hui
                ],
                "chong": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.chong
                ],
                "xing": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.xing
                ],
                "hai": [
                    {
                        "kind": i.kind,
                        "participants": list(i.participants),
                        "elements": list(i.elements),
                        "resulting_element": i.resulting_element,
                        "note": i.note,
                    }
                    for i in self.interactions.hai
                ],
                "citations": [self._citation_to_dict(c) for c in self.interactions.citations],
            },
            "all_citations": [self._citation_to_dict(c) for c in self.all_citations],
        }

    def explain(self) -> str:
        """
        Human-readable explanation with full rule citations.

        Use this for the "teaching mode" — every step traces back to
        a specific passage in 《子平真诠》.
        """
        lines: list[str] = []
        lines.append(f"=== 八字诊断 ===")
        lines.append(f"")
        lines.append(f"八字: {self.chart_summary}")
        lines.append(f"日主: {self.day_master}")
        lines.append(f"")

        # --- 用神 ---
        lines.append(f"--- 用神 ---")
        if self.yong_shen.stem:
            lines.append(f"用神: {self.yong_shen.stem} ({self.yong_shen.ten_god})")
        else:
            lines.append(f"用神: 未定（{self.yong_shen.citations[-1].conclusion}）")
        if self.yong_shen.transparent_stems:
            tss = ", ".join(
                f"{t.hidden_stem}({t.role})透于{t.transparent_at}干"
                for t in self.yong_shen.transparent_stems
            )
            lines.append(f"透干: {tss}")
        lines.append(f"")
        lines.append(f"推理链:")
        for c in self.yong_shen.citations:
            rule = get_rule(c.rule_id)
            lines.append(f"  [{c.rule_id}] ({rule.chapter})")
            lines.append(f"    原文: {rule.source_text}")
            lines.append(f"    现状: {c.reason}")
            lines.append(f"    结论: {c.conclusion}")
        lines.append(f"")

        # --- 格局 ---
        lines.append(f"--- 格局 ---")
        lines.append(f"格局: {self.ge_ju.name}")
        if self.ge_ju.alias:
            lines.append(f"又称: {self.ge_ju.alias}")
        lines.append(f"类别: {self.ge_ju.category}")
        if self.ge_ju.unresolved:
            lines.append(f"（注: 此格局用神无法在月令之外取定，标记为未定）")
        elif self.ge_ju.category == "建禄月劫" and self.yong_shen.is_bi_jie:
            lines.append(
                f"（注: 比劫当令，月令之外取{self.yong_shen.stem}"
                f"（{self.yong_shen.ten_god}）为用神）"
            )
        lines.append(f"")
        lines.append(f"推理链:")
        for c in self.ge_ju.citations:
            rule = get_rule(c.rule_id)
            lines.append(f"  [{c.rule_id}] ({rule.chapter})")
            lines.append(f"    原文: {rule.source_text}")
            lines.append(f"    现状: {c.reason}")
            lines.append(f"    结论: {c.conclusion}")
        lines.append(f"")

        # --- 相神/忌神 ---
        lines.append(f"--- 相神 / 忌神 ---")
        if self.xiang_shen.xiang_shen:
            xs = ", ".join(
                f"{o.stem}({o.ten_god})@{o.position}{o.location}"
                for o in self.xiang_shen.xiang_shen
            )
            lines.append(f"相神: {xs}")
        else:
            lines.append(f"相神: 无")
        if self.xiang_shen.ji_shen:
            js = ", ".join(
                f"{o.stem}({o.ten_god})@{o.position}{o.location}"
                for o in self.xiang_shen.ji_shen
            )
            lines.append(f"忌神: {js}")
        else:
            lines.append(f"忌神: 无")
        for note in self.xiang_shen.notes:
            lines.append(f"注: {note}")
        lines.append(f"")
        lines.append(f"推理链:")
        for c in self.xiang_shen.citations:
            rule = get_rule(c.rule_id)
            lines.append(f"  [{c.rule_id}] ({rule.chapter})")
            lines.append(f"    原文: {rule.source_text}")
            lines.append(f"    现状: {c.reason}")
            lines.append(f"    结论: {c.conclusion}")
        lines.append(f"")

        # --- 格局成败 ---
        lines.append(f"--- 格局成败 ---")
        lines.append(f"判定: {self.cheng_bai.verdict}")
        if self.cheng_bai.rescue_gods:
            rescues = ", ".join(
                f"{g.stem}({g.ten_god})" for g in self.cheng_bai.rescue_gods
            )
            lines.append(f"救神: {rescues}")
        lines.append(f"")
        lines.append(f"推理链:")
        for c in self.cheng_bai.citations:
            rule = get_rule(c.rule_id)
            lines.append(f"  [{c.rule_id}] ({rule.chapter})")
            lines.append(f"    原文: {rule.source_text}")
            lines.append(f"    现状: {c.reason}")
            lines.append(f"    结论: {c.conclusion}")
        lines.append(f"")

        # --- 刑冲合化 ---
        lines.append(f"--- 刑冲合化 ---")
        if not self.interactions.has_any():
            lines.append(f"无合冲刑害")
        else:
            ia = self.interactions
            if ia.gan_he:
                descs = "、".join(
                    f"{i.elements[0]}+{i.elements[1]}→{i.resulting_element}"
                    for i in ia.gan_he
                )
                lines.append(f"天干合: {descs}")
            if ia.san_he:
                descs = "、".join(
                    "+".join(i.elements) + f"→{i.resulting_element}"
                    for i in ia.san_he
                )
                lines.append(f"三合: {descs}")
            if ia.ban_he:
                descs = "、".join(
                    "+".join(i.elements) + f"→{i.resulting_element}（{i.note}）"
                    for i in ia.ban_he
                )
                lines.append(f"半三合: {descs}")
            if ia.san_hui:
                descs = "、".join(
                    "+".join(i.elements) + f"→{i.resulting_element}"
                    for i in ia.san_hui
                )
                lines.append(f"三会: {descs}")
            if ia.ban_hui:
                descs = "、".join(
                    "+".join(i.elements) + f"→{i.resulting_element}（{i.note}）"
                    for i in ia.ban_hui
                )
                lines.append(f"半三会: {descs}")
            if ia.chong:
                descs = "、".join(
                    f"{i.elements[0]}+{i.elements[1]}" for i in ia.chong
                )
                lines.append(f"六冲: {descs}")
            if ia.xing:
                descs = "、".join(
                    "+".join(i.elements) + f"（{i.note}）"
                    for i in ia.xing
                )
                lines.append(f"相刑: {descs}")
            if ia.hai:
                descs = "、".join(
                    f"{i.elements[0]}+{i.elements[1]}" for i in ia.hai
                )
                lines.append(f"相害: {descs}")
        lines.append(f"")
        lines.append(f"推理链:")
        for c in self.interactions.citations:
            rule = get_rule(c.rule_id)
            lines.append(f"  [{c.rule_id}] ({rule.chapter})")
            lines.append(f"    原文: {rule.source_text}")
            lines.append(f"    现状: {c.reason}")
            lines.append(f"    结论: {c.conclusion}")

        return "\n".join(lines)

    @staticmethod
    def _citation_to_dict(c: RuleCitation) -> dict:
        rule = get_rule(c.rule_id)
        return {
            "rule_id": c.rule_id,
            "chapter": rule.chapter,
            "source_text": rule.source_text,
            "modern_summary": rule.modern_summary,
            "reason": c.reason,
            "conclusion": c.conclusion,
        }


__all__ = ["Diagnosis"]
