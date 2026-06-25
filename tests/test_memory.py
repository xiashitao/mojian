"""User-level birth-info memory (save / get / clear)."""
import pytest

from web.backend import database
from web.backend.agent import memory
from web.backend.agent.models import BirthInfo

COMPLETE = BirthInfo(
    birth_date="1990-05-15", birth_time="08:00", longitude=116.4, gender="male"
)


@pytest.fixture()
def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "memory.db")
    database.init_db()


def test_save_get_clear_roundtrip(mem_db):
    assert memory.get_birth_info("k1") is None
    memory.save_birth_info("k1", COMPLETE)
    got = memory.get_birth_info("k1")
    assert got is not None and got.is_complete()
    assert got.birth_date == "1990-05-15"
    memory.clear("k1")
    assert memory.get_birth_info("k1") is None


def test_incomplete_is_not_saved(mem_db):
    memory.save_birth_info("k2", BirthInfo(birth_date="1990-05-15"))
    assert memory.get_birth_info("k2") is None


def test_no_key_is_noop(mem_db):
    memory.save_birth_info(None, COMPLETE)
    assert memory.get_birth_info(None) is None


def test_notes_add_recent_and_clear(mem_db):
    assert memory.recent_notes("nk") == []
    memory.add_note("nk", topic="career", question="事业怎么选", conclusion="适合稳健创业")
    memory.add_note("nk", topic="wealth", question="财运如何", conclusion="靠专业积累")
    notes = memory.recent_notes("nk")
    assert len(notes) == 2
    assert notes[0]["conclusion"] == "靠专业积累"  # newest first
    memory.clear("nk")
    assert memory.recent_notes("nk") == []


def test_note_without_conclusion_is_ignored(mem_db):
    memory.add_note("nk2", topic="career", question="q", conclusion="   ")
    assert memory.recent_notes("nk2") == []
