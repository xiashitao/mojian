"""Anonymous -> account migration on login/register."""
import pytest

from web.backend import database
from web.backend.agent import memory, repository
from web.backend.agent.models import BirthInfo
from web.backend.routers.auth import migrate_anonymous

BIRTH = BirthInfo(
    birth_date="1990-05-15", birth_time="08:00", longitude=116.4, gender="male"
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "auth.db")
    database.init_db()


def test_rekeys_conversations_and_memory(db):
    anon, user = "anon-123", "user-abc"
    conv = repository.ensure_conversation(None, user_id=anon)
    repository.add_message(conv["id"], "user", "你好")
    memory.save_birth_info(anon, BIRTH)
    memory.add_note(anon, topic="career", question="事业", conclusion="适合稳健发展")

    migrate_anonymous(anon, user)

    assert any(c["id"] == conv["id"] for c in repository.list_conversations(user_id=user))
    assert repository.list_conversations(user_id=anon) == []
    assert memory.get_birth_info(user) is not None
    assert memory.get_birth_info(anon) is None
    assert len(memory.recent_notes(user)) == 1
    assert memory.recent_notes(anon) == []


def test_keeps_accounts_existing_birth_info(db):
    anon, user = "anon-2", "user-2"
    memory.save_birth_info(user, BIRTH)  # account already has its own
    memory.save_birth_info(
        anon,
        BirthInfo(birth_date="1991-01-01", birth_time="01:00", longitude=121.5, gender="female"),
    )

    migrate_anonymous(anon, user)

    assert memory.get_birth_info(user).birth_date == "1990-05-15"  # account's own kept
    assert memory.get_birth_info(anon) is None


def test_noop_without_anon(db):
    migrate_anonymous(None, "user-x")
    migrate_anonymous("same", "same")  # no-op, must not raise
