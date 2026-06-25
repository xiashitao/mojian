"""Tests for the judgment/framing wall and the contextual-search guards."""
import pytest

from web.backend.agent.framing import (
    Judgment,
    ContextualSnippet,
    ContextualSearchProvider,
    DisabledContextualSearch,
    is_allowed_source,
    filter_snippets,
    build_context_query,
    gather_framing,
    REFERENCE_BLOCK_HEADER,
)


class _FakeProvider:
    """Test provider returning a fixed mix of allowed and denied sources."""

    def __init__(self, snippets):
        self._snippets = snippets

    def search(self, query, *, max_results=5):
        return list(self._snippets)[:max_results]


def _judgment(**kw):
    base = dict(topic="career", ge_ju="偏财格", yong_shen_ten_god="偏财")
    base.update(kw)
    return Judgment(**base)


class TestWallIsStructural:
    def test_judgment_is_frozen(self):
        j = _judgment()
        with pytest.raises(Exception):
            j.ge_ju = "正财格"  # type: ignore

    def test_disabled_provider_is_default_and_noop(self):
        fc = gather_framing(_judgment())
        assert fc.snippets == []
        assert fc.render_reference_block() == ""
        # Trace always declares it cannot affect judgment.
        assert fc.trace_payload()["affects_judgment"] is False
        assert fc.trace_payload()["channel"] == "contextual"

    def test_default_provider_type(self):
        assert isinstance(DisabledContextualSearch(), ContextualSearchProvider)


class TestSourceGuard:
    def test_denies_mingli_marketing_sources(self):
        assert is_allowed_source("https://www.suanming123.com/x") is False
        assert is_allowed_source("https://八字算命.cn/a") is False
        assert is_allowed_source("https://example.com/jobs-2026") is True
        assert is_allowed_source(None) is True

    def test_filter_drops_denied_and_empty(self):
        snippets = [
            ContextualSnippet(title="行业趋势", snippet="制造业回暖", source_url="https://news.example.com/a"),
            ContextualSnippet(title="算命大师", snippet="你命中有财", source_url="https://suanming.cn/b"),
            ContextualSnippet(title="空的", snippet="   ", source_url="https://example.com/c"),
        ]
        out = filter_snippets(snippets)
        assert len(out) == 1
        assert out[0].title == "行业趋势"

    def test_filter_restamps_kind(self):
        sneaky = ContextualSnippet(title="t", snippet="s", source_url="https://example.com")
        sneaky = sneaky.model_copy(update={"kind": "verdict"})
        out = filter_snippets([sneaky])
        assert out[0].kind == "contextual_reference"


class TestQueryBuilding:
    def test_query_is_era_stamped_and_pure(self):
        q = build_context_query(_judgment(), year=2026)
        assert q is not None and "2026" in q
        # Pure: same inputs -> same query.
        assert q == build_context_query(_judgment(), year=2026)

    def test_query_avoids_jargon(self):
        q = build_context_query(_judgment(topic="career"), year=2026)
        # Translates to a plain modern theme, not 命理 jargon.
        assert "偏财" not in q and "格" not in q

    def test_no_query_for_unknown_topic(self):
        assert build_context_query(Judgment(topic=None)) is None


class TestGatherFraming:
    def test_allowed_snippets_render_in_labelled_block(self):
        provider = _FakeProvider([
            ContextualSnippet(title="2026就业", snippet="灵活就业上升", source_url="https://news.example.com/x"),
            ContextualSnippet(title="营销站", snippet="改运套餐", source_url="https://dashi.suanming.cn/y"),
        ])
        fc = gather_framing(_judgment(), provider=provider, year=2026)
        # Denied source filtered out; one survives.
        assert len(fc.snippets) == 1
        block = fc.render_reference_block()
        assert REFERENCE_BLOCK_HEADER in block
        assert "不得" in block  # the guard instruction is present
        assert "2026就业" in block

    def test_trace_payload_separate_channel(self):
        provider = _FakeProvider([
            ContextualSnippet(title="t", snippet="s", source_url="https://example.com/x"),
        ])
        fc = gather_framing(_judgment(), provider=provider, year=2026)
        payload = fc.trace_payload()
        assert payload["channel"] == "contextual"
        assert payload["affects_judgment"] is False
        assert payload["snippet_count"] == 1
