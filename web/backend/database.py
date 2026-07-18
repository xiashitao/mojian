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

# 邮箱登录验证码（每邮箱一条活跃记录，新发即覆盖）。
_CREATE_EMAIL_CODES = """
CREATE TABLE IF NOT EXISTS email_codes (
    email       TEXT PRIMARY KEY,
    code        TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    sent_at     TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

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
    memory_key      TEXT NOT NULL,
    subject         TEXT NOT NULL DEFAULT 'self',
    birth_info_json TEXT NOT NULL DEFAULT '{}',
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (memory_key, subject)
)
"""

# memory_text:agent 自主记忆——模型每轮自行判断「这轮有什么值得长期记住的
# 用户信息」写下的自由文本(用户明确说出的处境/计划/事实),与 conclusion
# (结论摘要)互补。可空;干支等命理术语在写入前净化。
_CREATE_USER_MEMORY_NOTES = """
CREATE TABLE IF NOT EXISTS user_memory_notes (
    id          TEXT PRIMARY KEY,
    memory_key  TEXT NOT NULL,
    subject     TEXT NOT NULL DEFAULT 'self',
    topic       TEXT,
    question    TEXT,
    conclusion  TEXT,
    memory_text TEXT,
    analysis_id TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_USER_MEMORY_NOTES_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_memory_notes_key "
    "ON user_memory_notes(memory_key, subject, created_at)",
)

# 用户画像:从历次咨询里沉淀的稳定特征(人生阶段/核心关切/性格/目标/沟通偏好)。
# 与 user_memory(出生信息)平行,但记录的是「这个人是谁」而非「他的八字」。
# turns_since_update 是计数器,主流程每轮 +1,达到阈值后触发 LLM 批量更新。
# 主键含 subject:每个主体一个独立画像(用户本人 vs 配偶 vs 子女各不混淆)。
_CREATE_USER_PROFILE = """
CREATE TABLE IF NOT EXISTS user_profile (
    memory_key          TEXT NOT NULL,
    subject             TEXT NOT NULL DEFAULT 'self',
    life_stage          TEXT,
    core_concerns       TEXT,
    traits              TEXT,
    long_term_goal      TEXT,
    comm_style          TEXT,
    raw_summary         TEXT,
    turns_since_update  INTEGER NOT NULL DEFAULT 0,
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (memory_key, subject)
)
"""

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

# 每轮 run 的 LLM 开销(CostMeter observer 在 run 结束时写入)。
# cost 单位为元(CNY),按「记录时定价」计——价格表日后调整不影响历史数据;
# NULL = 该轮所用模型无定价(不知道就说不知道,不填 0 冒充)。
# models_json 存按模型分桶的明细 {model: {calls, prompt_tokens, completion_tokens, cost}}。
_CREATE_RUN_COSTS = """
CREATE TABLE IF NOT EXISTS run_costs (
    run_id            TEXT PRIMARY KEY,
    conversation_id   TEXT NOT NULL,
    llm_calls         INTEGER NOT NULL DEFAULT 0,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens      INTEGER NOT NULL DEFAULT 0,
    cost              REAL,
    models_json       TEXT NOT NULL DEFAULT '{}',
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES agent_runs(id)
)
"""

_CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_agent_runs_conversation ON agent_runs(conversation_id, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_run_traces_run ON run_traces(run_id, step_index)",
    "CREATE INDEX IF NOT EXISTS idx_agent_runs_analysis ON agent_runs(public_analysis_id)",
    "CREATE INDEX IF NOT EXISTS idx_run_costs_created ON run_costs(created_at)",
)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _table_pk(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return the PK column names of a table (empty if none / table missing)."""
    try:
        row = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.Error:
        return []
    return [r["name"] for r in row if r["pk"]]


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    """Add a column if the table doesn't have it yet (idempotent light migration).

    SQLite's ALTER TABLE ADD COLUMN is cheap (no table rebuild), so this is the
    right tool for additive schema evolution — heavier changes (PK rework) go
    through the rebuild path like _migrate_subject_schema."""
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if cols and column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _migrate_subject_schema(conn: sqlite3.Connection) -> None:
    """Migrate user_memory / user_memory_notes / user_profile from single-PK
    (memory_key only) to composite-PK (memory_key, subject).

    Old tables had no `subject` column; the new schema defaults it to 'self'.
    SQLite can't ALTER a primary key, so we rebuild: rename old → create new
    with composite PK → copy rows (subject='self') → drop old.

    Robust to historical schema variance: only columns that ACTUALLY exist in
    the old table are copied; missing ones fall back to the new column's
    DEFAULT (so an old user_profile without core_concerns still migrates,
    with core_concerns becoming NULL).

    Idempotent: if a table already has the new schema (PK includes subject),
    it's a no-op. Safe to run on every init_db().
    """
    # New-column order per table, in the order the new CREATE TABLE declares.
    new_columns = {
        "user_memory": ["memory_key", "subject", "birth_info_json", "updated_at"],
        "user_memory_notes": ["id", "memory_key", "subject", "topic", "question",
                              "conclusion", "analysis_id", "created_at"],
        "user_profile": ["memory_key", "subject", "life_stage", "core_concerns",
                         "traits", "long_term_goal", "comm_style", "raw_summary",
                         "turns_since_update", "updated_at"],
    }
    create_sql = {
        "user_memory": _CREATE_USER_MEMORY,
        "user_memory_notes": _CREATE_USER_MEMORY_NOTES,
        "user_profile": _CREATE_USER_PROFILE,
    }
    for table, cols in new_columns.items():
        pk = _table_pk(conn, table)
        if "subject" in pk:        # already new schema
            continue
        if not pk:                 # table missing → CREATE makes it fresh
            continue
        # Old schema → rebuild. First record which columns exist in the old table.
        old_cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        backup = f"{table}__old_{int(__import__('time').time())}"
        conn.execute(f"ALTER TABLE {table} RENAME TO {backup}")
        conn.execute(create_sql[table])
        # Build column list + matching SELECT expressions, but ONLY for columns
        # we have a value for (subject → literal 'self'; others → old column name).
        # Columns missing from the old table are OMITTED from the INSERT, so the
        # new column's DEFAULT fills in (avoids NOT NULL violations on columns
        # like updated_at that have a DEFAULT but no value in the old table).
        insert_cols = []
        select_exprs = []
        for c in cols:
            if c == "subject":
                insert_cols.append(c)
                select_exprs.append("'self'")
            elif c in old_cols:
                insert_cols.append(c)
                select_exprs.append(c)
            # else: skip — new column keeps its declared DEFAULT
        conn.execute(f"INSERT INTO {table} ({', '.join(insert_cols)}) "
                     f"SELECT {', '.join(select_exprs)} FROM {backup}")
        conn.execute(f"DROP TABLE {backup}")


def init_db():
    conn = get_db()
    try:
        conn.execute(_CREATE_USERS)
        conn.execute(_CREATE_EMAIL_CODES)
        conn.execute(_CREATE_SAVED_CHARTS)
        conn.execute(_CREATE_USER_MEMORY)
        conn.execute(_CREATE_USER_MEMORY_NOTES)
        conn.execute(_CREATE_USER_PROFILE)
        conn.execute(_CREATE_CONVERSATIONS)
        conn.execute(_CREATE_MESSAGES)
        conn.execute(_CREATE_AGENT_RUNS)
        conn.execute(_CREATE_RUN_TRACES)
        conn.execute(_CREATE_RUN_COSTS)
        # Migrate legacy single-PK tables to the new (memory_key, subject) schema.
        # Idempotent; runs on every init but is a no-op once migrated.
        _migrate_subject_schema(conn)
        # 轻量列迁移:老库补 memory_text 列(幂等)。
        _ensure_column(conn, "user_memory_notes", "memory_text", "TEXT")
        for statement in _CREATE_INDEXES:
            conn.execute(statement)
        for statement in _CREATE_USERS_INDEX:
            conn.execute(statement)
        for statement in _CREATE_USER_MEMORY_NOTES_INDEX:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()
