"""Bazibase tool-result caching by birth determinants (Cache pillar)."""
from web.backend.agent.models import BirthInfo
from web.backend.agent.tools import _TOOL_CACHE, run_bazibase_tools

BIRTH = BirthInfo(
    birth_date="1990-05-15", birth_time="08:00", longitude=116.4, gender="male"
)


def test_same_birth_served_from_cache():
    _TOOL_CACHE.clear()
    first = run_bazibase_tools(BIRTH)
    second = run_bazibase_tools(BIRTH)
    assert first is second  # computed once, reused on the follow-up turn


def test_different_birth_not_shared():
    _TOOL_CACHE.clear()
    first = run_bazibase_tools(BIRTH)
    other = BirthInfo(
        birth_date="1991-06-16", birth_time="09:30", longitude=121.5, gender="female"
    )
    assert first is not run_bazibase_tools(other)
