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
