import json
import sqlite3
import logging
from datetime import datetime
from backend.models.learner import LearnerState
from backend.models.events import Session
from backend.models.journal import JournalEntry, LearnerJournal
from backend.config import settings

logger = logging.getLogger(__name__)


def _is_postgres() -> bool:
    return settings.database_url.startswith("postgresql")


class LearnerStore:

    def __init__(self):
        if not _is_postgres():
            self.db_path = settings.sqlite_path
            self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learners (
                learner_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                learner_id TEXT,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    async def create_learner(self, learner: LearnerState) -> LearnerState:
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO learners (learner_id, data, created_at, last_active) "
                    "VALUES ($1, $2, $3, $4)",
                    learner.learner_id,
                    learner.model_dump_json(),
                    learner.created_at,
                    learner.last_active,
                )
        else:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO learners (learner_id, data, created_at, last_active) VALUES (?, ?, ?, ?)",
                (learner.learner_id, learner.model_dump_json(),
                 learner.created_at.isoformat(), learner.last_active.isoformat()),
            )
            conn.commit()
            conn.close()
        return learner

    async def get_learner(self, learner_id: str) -> LearnerState | None:
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT data FROM learners WHERE learner_id = $1", learner_id,
                )
            if not row:
                return None
            return LearnerState.model_validate_json(row["data"])
        else:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT data FROM learners WHERE learner_id = ?", (learner_id,),
            ).fetchone()
            conn.close()
            if not row:
                return None
            return LearnerState.model_validate_json(row[0])

    async def update_learner(self, learner: LearnerState):
        learner.last_active = datetime.utcnow()
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE learners SET data = $1, last_active = $2 WHERE learner_id = $3",
                    learner.model_dump_json(),
                    learner.last_active,
                    learner.learner_id,
                )
        else:
            conn = self._get_conn()
            conn.execute(
                "UPDATE learners SET data = ?, last_active = ? WHERE learner_id = ?",
                (learner.model_dump_json(), learner.last_active.isoformat(), learner.learner_id),
            )
            conn.commit()
            conn.close()

    async def save_session(self, session: Session):
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO sessions (session_id, learner_id, data, created_at) "
                    "VALUES ($1, $2, $3, $4) "
                    "ON CONFLICT (session_id) DO UPDATE SET data = EXCLUDED.data",
                    session.session_id,
                    session.learner_id,
                    session.model_dump_json(),
                    session.started_at,
                )
        else:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, learner_id, data, created_at) VALUES (?, ?, ?, ?)",
                (session.session_id, session.learner_id,
                 session.model_dump_json(), session.started_at.isoformat()),
            )
            conn.commit()
            conn.close()

    async def get_session(self, session_id: str) -> Session | None:
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT data FROM sessions WHERE session_id = $1", session_id,
                )
            if not row:
                return None
            return Session.model_validate_json(row["data"])
        else:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT data FROM sessions WHERE session_id = ?", (session_id,),
            ).fetchone()
            conn.close()
            if not row:
                return None
            return Session.model_validate_json(row[0])

    async def get_learner_sessions(self, learner_id: str) -> list[Session]:
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT data FROM sessions WHERE learner_id = $1 ORDER BY created_at DESC",
                    learner_id,
                )
            return [Session.model_validate_json(r["data"]) for r in rows]
        else:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT data FROM sessions WHERE learner_id = ? ORDER BY created_at DESC",
                (learner_id,),
            ).fetchall()
            conn.close()
            return [Session.model_validate_json(r[0]) for r in rows]


    async def save_journal_entry(self, learner_id: str, entry: JournalEntry):
        data = entry.model_dump_json()
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO journal_entries (entry_id, learner_id, data, created_at) "
                    "VALUES ($1, $2, $3, $4) "
                    "ON CONFLICT (entry_id) DO UPDATE SET data = EXCLUDED.data",
                    entry.entry_id, learner_id, data, entry.timestamp or datetime.utcnow().isoformat(),
                )
        else:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO journal_entries (entry_id, learner_id, data, created_at) VALUES (?, ?, ?, ?)",
                (entry.entry_id, learner_id, data, entry.timestamp or datetime.utcnow().isoformat()),
            )
            conn.commit()
            conn.close()

    async def get_journal(self, learner_id: str) -> LearnerJournal:
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT data FROM journal_entries WHERE learner_id = $1 ORDER BY created_at DESC",
                    learner_id,
                )
            entries = [JournalEntry.model_validate_json(r["data"]) for r in rows]
        else:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT data FROM journal_entries WHERE learner_id = ? ORDER BY created_at DESC",
                (learner_id,),
            ).fetchall()
            conn.close()
            entries = [JournalEntry.model_validate_json(r[0]) for r in rows]
        return LearnerJournal(learner_id=learner_id, entries=entries)

    async def create_user(self, user_id: str, email: str, password_hash: str, learner_id: str):
        now = datetime.utcnow()
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO users (user_id, email, password_hash, learner_id, created_at) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    user_id, email, password_hash, learner_id, now,
                )
        else:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO users (user_id, email, password_hash, learner_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, email, password_hash, learner_id, now.isoformat()),
            )
            conn.commit()
            conn.close()

    async def get_user_by_email(self, email: str) -> dict | None:
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT user_id, email, password_hash, learner_id, is_active FROM users WHERE email = $1", email,
                )
            if not row:
                return None
            return dict(row)
        else:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT user_id, email, password_hash, learner_id, is_active FROM users WHERE email = ?", (email,),
            ).fetchone()
            conn.close()
            if not row:
                return None
            return dict(row)

    async def get_user_by_id(self, user_id: str) -> dict | None:
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT user_id, email, password_hash, learner_id, is_active FROM users WHERE user_id = $1", user_id,
                )
            if not row:
                return None
            return dict(row)
        else:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT user_id, email, password_hash, learner_id, is_active FROM users WHERE user_id = ?", (user_id,),
            ).fetchone()
            conn.close()
            if not row:
                return None
            return dict(row)


learner_store = LearnerStore()
