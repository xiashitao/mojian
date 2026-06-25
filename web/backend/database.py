"""SQLite connection + application tables."""
import sqlite3
from .config import DB_PATH

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL DEFAULT 'user'
                  CHECK(role IN ('user', 'pro', 'max', 'admin')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_USERS_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
)

_CREATE_SAVED_CHARTS = """
CREATE TABLE IF NOT EXISTS saved_charts (
    id          TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    date        TEXT NOT NULL,
    time        TEXT NOT NULL,
    longitude   REAL NOT NULL,
    gender      TEXT NOT NULL,
    tz_offset   REAL NOT NULL DEFAULT 8.0,
    solar_correction INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_USER_MEMORY = """
CREATE TABLE IF NOT EXISTS user_memory (
    memory_key      TEXT PRIMARY KEY,
    birth_info_json TEXT NOT NULL DEFAULT '{}',
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_USER_MEMORY_NOTES = """
CREATE TABLE IF NOT EXISTS user_memory_notes (
    id          TEXT PRIMARY KEY,
    memory_key  TEXT NOT NULL,
    topic       TEXT,
    question    TEXT,
    conclusion  TEXT,
    analysis_id TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_USER_MEMORY_NOTES_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_memory_notes_key "
    "ON user_memory_notes(memory_key, created_at)",
)

_CREATE_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    user_id         TEXT,
    title           TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_message_at TEXT,
    metadata_json   TEXT NOT NULL DEFAULT '{}'
)
"""

_CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    analysis_id     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
)
"""

_CREATE_AGENT_RUNS = """
CREATE TABLE IF NOT EXISTS agent_runs (
    id                  TEXT PRIMARY KEY,
    conversation_id     TEXT NOT NULL,
    trigger_message_id  TEXT NOT NULL,
    assistant_message_id TEXT,
    public_analysis_id  TEXT NOT NULL UNIQUE,
    status              TEXT NOT NULL DEFAULT 'partial',
    intent              TEXT,
    topic               TEXT,
    model               TEXT,
    started_at          TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at         TEXT,
    latency_ms          INTEGER,
    error               TEXT,
    metadata_json       TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (trigger_message_id) REFERENCES messages(id),
    FOREIGN KEY (assistant_message_id) REFERENCES messages(id)
)
"""

_CREATE_RUN_TRACES = """
CREATE TABLE IF NOT EXISTS run_traces (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL,
    step_index  INTEGER NOT NULL,
    step_type   TEXT NOT NULL,
    input_json  TEXT NOT NULL DEFAULT '{}',
    output_json TEXT NOT NULL DEFAULT '{}',
    summary     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES agent_runs(id)
)
"""

_CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_agent_runs_conversation ON agent_runs(conversation_id, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_run_traces_run ON run_traces(run_id, step_index)",
    "CREATE INDEX IF NOT EXISTS idx_agent_runs_analysis ON agent_runs(public_analysis_id)",
)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute(_CREATE_USERS)
        conn.execute(_CREATE_SAVED_CHARTS)
        conn.execute(_CREATE_USER_MEMORY)
        conn.execute(_CREATE_USER_MEMORY_NOTES)
        conn.execute(_CREATE_CONVERSATIONS)
        conn.execute(_CREATE_MESSAGES)
        conn.execute(_CREATE_AGENT_RUNS)
        conn.execute(_CREATE_RUN_TRACES)
        for statement in _CREATE_INDEXES:
            conn.execute(statement)
        for statement in _CREATE_USERS_INDEX:
            conn.execute(statement)
        for statement in _CREATE_USER_MEMORY_NOTES_INDEX:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()
