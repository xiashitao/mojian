"""
bazibase.rules.schema
=====================

Rule schema for Layer 2.

A `Rule` is a citation record — NOT an executable. The actual rule
application logic lives in `yong_shen.py`, `ge_ju.py`, etc. Each step
of those algorithms cites a Rule by id, so the output Diagnosis can
always trace back to specific 《子平真诠》 text.

This design is deliberate: encoding 子平派 rules as a fully declarative
condition/action language would be over-engineering, because most of
the rule application is fundamentally a deterministic algorithm
(especially 用神取法). Code is more honest than config here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    """
    A citation record for a 《子平真诠》 rule.

    Attributes:
        id: Stable identifier like "ZP-YONG-001". Format:
            ZP-{CHAPTER}-{SEQ}, where CHAPTER is:
              YONG = 论用神 chapter family
              GE   = 论格局 chapter family
              XIANG = 论相神
        chapter: Human-readable chapter like "子平真诠·论用神"
        source_text: Original Chinese text being cited.
        modern_summary: Modern Chinese explanation.
        category: "yong_shen" / "ge_ju" / "xiang_shen" / "conflict"
        priority: Lower = higher priority when rules conflict.
    """
    id: str
    chapter: str
    source_text: str
    modern_summary: str
    category: str
    priority: int = 50


# ---------------------------------------------------------------------------
# Registered rule library
# ---------------------------------------------------------------------------

# Populated by the `register_rule` calls in yong_shen.py and ge_ju.py.
_RULE_LIBRARY: dict[str, Rule] = {}


def register_rule(rule: Rule) -> Rule:
    """Register a Rule in the global library. Returns the rule."""
    if rule.id in _RULE_LIBRARY:
        raise ValueError(f"Rule id {rule.id!r} already registered")
    _RULE_LIBRARY[rule.id] = rule
    return rule


def get_rule(rule_id: str) -> Rule:
    """Look up a registered rule by id."""
    if rule_id not in _RULE_LIBRARY:
        raise KeyError(f"Unknown rule id: {rule_id!r}")
    return _RULE_LIBRARY[rule_id]


def all_rules() -> list[Rule]:
    """Return all registered rules (mostly for introspection/testing)."""
    return sorted(_RULE_LIBRARY.values(), key=lambda r: (r.category, r.priority, r.id))


# ---------------------------------------------------------------------------
# Rule citation in a Diagnosis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RuleCitation:
    """
    A specific application of a Rule in a Diagnosis.

    This is what shows up in the output: "we applied rule X because
    condition Y held, and concluded Z".
    """
    rule_id: str
    reason: str           # why this rule fired (the trigger condition)
    conclusion: str       # what we concluded


__all__ = [
    "Rule",
    "RuleCitation",
    "register_rule",
    "get_rule",
    "all_rules",
]
