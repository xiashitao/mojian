"""
framing — the wall between deterministic judgment and era-contextual framing.

《易》有三义：不易、变易、简易。命理这套东西同时含「不易」与「变易」：

    不易  规则体系（用神/格局/成败/旺衰）—— 确定性、可溯源、进规则链。
    变易  内生之变 = 大运/流年（已由 bazibase 确定性算出）；
          外生之变 = 时代语境（同一结构在不同时代落到的现实载体不同）。

This module governs ONLY the *外生之变* layer. It exists to let era-aware,
optionally web-sourced context enrich how a conclusion is *phrased and
localised to the present day* — WITHOUT ever touching the deterministic
吉凶 verdict or entering the traceable rule chain.

The wall is structural, not just documented:

    - `Judgment` is frozen. The framing layer is handed a read-only view of
      the deterministic conclusion and has no API to mutate it.
    - Contextual search is OFF by default (`DisabledContextualSearch`). It is
      opt-in and injected, never reached implicitly.
    - Every snippet is tagged `kind="contextual_reference"`, rendered under a
      clearly-labelled「时代语境参考」block, and surfaced in the trace under a
      separate `contextual` channel — never merged into `cast_chart` /
      `diagnose` / `arbitrate` outputs.
    - `gather_framing` filters out 玄学/命理营销 sources, so the model is not
      fed the very 恐吓/断语 style PRODUCT.md rejects.

The responder prompt gets the rule-based judgment as ground truth plus this
reference block as *background only*, with an explicit instruction that the
background must never contradict or override the deterministic verdict.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from .models import Topic


# ---------------------------------------------------------------------------
# Read-only view of the deterministic conclusion (the 不易 + 内生变易 layer)
# ---------------------------------------------------------------------------

class Judgment(BaseModel):
    """A frozen, read-only projection of the deterministic analysis.

    Built from the same structured result the responder already assembles
    (chart + diagnosis + arbitration). The framing layer may *read* this to
    decide what era-context to fetch, but cannot change it.
    """
    model_config = {"frozen": True}

    topic: Optional[Topic] = None
    ge_ju: Optional[str] = None                 # 格局名，如「偏财格」
    yong_shen_ten_god: Optional[str] = None     # 用神十神
    strength_verdict: Optional[str] = None      # 身强/身弱…
    cheng_bai: Optional[str] = None             # 成败状态（确定性 verdict）
    current_luck_pillar: Optional[str] = None   # 当前大运干支（内生之变）
    current_year_pillar: Optional[str] = None   # 当前流年干支（内生之变）


# ---------------------------------------------------------------------------
# Contextual snippets and the search provider boundary
# ---------------------------------------------------------------------------

class ContextualSnippet(BaseModel):
    """A single piece of era-context. Background reference ONLY."""
    kind: str = "contextual_reference"          # never anything else
    title: str
    snippet: str
    source_url: Optional[str] = None


@runtime_checkable
class ContextualSearchProvider(Protocol):
    """Injectable web/context search. Implementations stay outside this module."""

    def search(self, query: str, *, max_results: int = 5) -> list[ContextualSnippet]:
        ...


class DisabledContextualSearch:
    """Default provider: no search. Contextual search is opt-in, never implicit."""

    def search(self, query: str, *, max_results: int = 5) -> list[ContextualSnippet]:
        return []


# Sources whose 命理/玄学营销 framing would pollute the restrained advisor tone
# (see PRODUCT.md Anti-references). Matched as case-insensitive substrings of
# the host / url. Extend via config rather than hard-coding business logic.
DENY_SOURCE_SUBSTRINGS: tuple[str, ...] = (
    "suanming", "算命", "八字", "风水", "fengshui", "算卦", "周易预测",
    "测算", "运势大全", "大师在线", "塔罗", "占卜",
)


def is_allowed_source(url: str | None) -> bool:
    """False for 玄学/命理营销 domains we refuse to feed back into the model."""
    if not url:
        return True  # snippets without a URL (e.g. model-internal) are allowed
    low = url.lower()
    return not any(bad.lower() in low for bad in DENY_SOURCE_SUBSTRINGS)


def filter_snippets(snippets: list[ContextualSnippet]) -> list[ContextualSnippet]:
    """Drop disallowed sources and force the contextual_reference tag."""
    out: list[ContextualSnippet] = []
    for s in snippets:
        if not is_allowed_source(s.source_url):
            continue
        if not s.snippet.strip():
            continue
        # Re-stamp the kind so a provider can never smuggle a different label.
        out.append(s.model_copy(update={"kind": "contextual_reference"}))
    return out


# ---------------------------------------------------------------------------
# Query building — derived from the structured judgment, not the user's words
# ---------------------------------------------------------------------------

# Map a 命理 signal to a plain-language MODERN theme. We deliberately translate
# away from jargon: the query asks about present-day domains, never about fate.
_TOPIC_THEME: dict[str, str] = {
    "career": "适合的现代职业方向与行业趋势",
    "wealth": "现代收入与理财方式的现实选择",
    "relationship": "当代亲密关系与相处方式",
    "personality": "个人优势在当代环境中的发挥方式",
}


def build_context_query(judgment: Judgment, *, year: int | None = None) -> str | None:
    """Build a neutral, era-stamped context query from the judgment.

    Pure function (no clock access): the caller passes `year` so the query
    stays reproducible and trace-stable. Returns None when there's nothing
    worth contextualising.
    """
    theme = _TOPIC_THEME.get(judgment.topic or "", "")
    if not theme:
        return None
    era = f"{year} 年" if year else "当下"
    return f"{era}{theme}"


# ---------------------------------------------------------------------------
# The framing context: judgment (read-only) + background snippets
# ---------------------------------------------------------------------------

REFERENCE_BLOCK_HEADER = "## 时代语境参考（仅供叙述落地，不得改变上方判断）"

_FRAMING_GUARD = (
    "以下条目是当代背景参考，只能用来把结论「翻译」成这个时代的具体说法，"
    "不得与上方确定性的吉凶判断冲突，也不得据此推翻或加重任何结论。"
)


class FramingContext(BaseModel):
    """Bundles the read-only judgment with era-context snippets."""
    judgment: Judgment
    snippets: list[ContextualSnippet] = Field(default_factory=list)
    query: Optional[str] = None

    def render_reference_block(self) -> str:
        """Prompt fragment for the responder. Empty when there's no context."""
        if not self.snippets:
            return ""
        lines = [REFERENCE_BLOCK_HEADER, _FRAMING_GUARD]
        for s in self.snippets:
            src = f"（来源：{s.source_url}）" if s.source_url else ""
            lines.append(f"- {s.title}：{s.snippet}{src}")
        return "\n".join(lines)

    def trace_payload(self) -> dict:
        """Trace entry tagged as a SEPARATE contextual channel.

        Deliberately NOT part of the cast_chart/diagnose/arbitrate chain, so a
        reviewer can always tell rule-based judgment from era framing.
        """
        return {
            "channel": "contextual",          # not "rule_chain"
            "query": self.query,
            "snippet_count": len(self.snippets),
            "snippets": [s.model_dump() for s in self.snippets],
            "affects_judgment": False,         # invariant of this layer
        }


def gather_framing(
    judgment: Judgment,
    *,
    provider: ContextualSearchProvider | None = None,
    year: int | None = None,
    max_results: int = 5,
) -> FramingContext:
    """Fetch era-context for a judgment, fully guarded.

    With the default (disabled) provider this is a no-op that returns an empty
    FramingContext — so wiring this in changes nothing until a real provider
    is injected. Even then, results pass the source guard and never touch the
    judgment.
    """
    provider = provider or DisabledContextualSearch()
    query = build_context_query(judgment, year=year)
    if not query:
        return FramingContext(judgment=judgment, snippets=[], query=None)

    raw = provider.search(query, max_results=max_results)
    snippets = filter_snippets(list(raw))[:max_results]
    return FramingContext(judgment=judgment, snippets=snippets, query=query)


__all__ = [
    "Judgment",
    "ContextualSnippet",
    "ContextualSearchProvider",
    "DisabledContextualSearch",
    "DENY_SOURCE_SUBSTRINGS",
    "is_allowed_source",
    "filter_snippets",
    "build_context_query",
    "FramingContext",
    "gather_framing",
    "REFERENCE_BLOCK_HEADER",
]
