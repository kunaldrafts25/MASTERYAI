import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timezone
from backend.models.learner import LearnerState
from backend.models.events import Session
from backend.models.journal import JournalEntry, LearnerJournal
from backend.config import settings

logger = logging.getLogger(__name__)


def _is_postgres() -> bool:
    return settings.database_url.startswith("postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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

    # ── Helper: run blocking SQLite in a thread ──────────────────────────

    @staticmethod
    async def _run(fn, *args):
        return await asyncio.to_thread(fn, *args)

    # ── Learner CRUD ─────────────────────────────────────────────────────

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
            def _do(lid, data, created, active):
                conn = self._get_conn()
                conn.execute(
                    "INSERT INTO learners (learner_id, data, created_at, last_active) VALUES (?, ?, ?, ?)",
                    (lid, data, created, active),
                )
                conn.commit()
                conn.close()
            await self._run(_do, learner.learner_id, learner.model_dump_json(),
                            learner.created_at.isoformat(), learner.last_active.isoformat())
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
            def _do(lid):
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT data FROM learners WHERE learner_id = ?", (lid,),
                ).fetchone()
                conn.close()
                return row
            row = await self._run(_do, learner_id)
            if not row:
                return None
            return LearnerState.model_validate_json(row[0])

    async def update_learner(self, learner: LearnerState):
        learner.last_active = _utcnow()
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
            def _do(lid, data, active):
                conn = self._get_conn()
                conn.execute(
                    "UPDATE learners SET data = ?, last_active = ? WHERE learner_id = ?",
                    (data, active, lid),
                )
                conn.commit()
                conn.close()
            await self._run(_do, learner.learner_id, learner.model_dump_json(),
                            learner.last_active.isoformat())

    # ── Session CRUD ─────────────────────────────────────────────────────

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
            def _do(sid, lid, data, created):
                conn = self._get_conn()
                conn.execute(
                    "INSERT OR REPLACE INTO sessions (session_id, learner_id, data, created_at) VALUES (?, ?, ?, ?)",
                    (sid, lid, data, created),
                )
                conn.commit()
                conn.close()
            await self._run(_do, session.session_id, session.learner_id,
                            session.model_dump_json(), session.started_at.isoformat())

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
            def _do(sid):
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT data FROM sessions WHERE session_id = ?", (sid,),
                ).fetchone()
                conn.close()
                return row
            row = await self._run(_do, session_id)
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
            def _do(lid):
                conn = self._get_conn()
                rows = conn.execute(
                    "SELECT data FROM sessions WHERE learner_id = ? ORDER BY created_at DESC",
                    (lid,),
                ).fetchall()
                conn.close()
                return rows
            rows = await self._run(_do, learner_id)
            return [Session.model_validate_json(r[0]) for r in rows]

    # ── Journal ──────────────────────────────────────────────────────────

    async def save_journal_entry(self, learner_id: str, entry: JournalEntry):
        data = entry.model_dump_json()
        ts = entry.timestamp or _utcnow().isoformat()
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO journal_entries (entry_id, learner_id, data, created_at) "
                    "VALUES ($1, $2, $3, $4) "
                    "ON CONFLICT (entry_id) DO UPDATE SET data = EXCLUDED.data",
                    entry.entry_id, learner_id, data, ts,
                )
        else:
            def _do(eid, lid, d, t):
                conn = self._get_conn()
                conn.execute(
                    "INSERT OR REPLACE INTO journal_entries (entry_id, learner_id, data, created_at) VALUES (?, ?, ?, ?)",
                    (eid, lid, d, t),
                )
                conn.commit()
                conn.close()
            await self._run(_do, entry.entry_id, learner_id, data, ts)

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
            def _do(lid):
                conn = self._get_conn()
                rows = conn.execute(
                    "SELECT data FROM journal_entries WHERE learner_id = ? ORDER BY created_at DESC",
                    (lid,),
                ).fetchall()
                conn.close()
                return rows
            rows = await self._run(_do, learner_id)
            entries = [JournalEntry.model_validate_json(r[0]) for r in rows]
        return LearnerJournal(learner_id=learner_id, entries=entries)

    # ── User auth ────────────────────────────────────────────────────────

    async def create_user(self, user_id: str, email: str, password_hash: str, learner_id: str):
        now = _utcnow()
        if _is_postgres():
            from backend.db.database import db
            async with db.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO users (user_id, email, password_hash, learner_id, created_at) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    user_id, email, password_hash, learner_id, now,
                )
        else:
            def _do(uid, em, pw, lid, ts):
                conn = self._get_conn()
                conn.execute(
                    "INSERT INTO users (user_id, email, password_hash, learner_id, created_at) VALUES (?, ?, ?, ?, ?)",
                    (uid, em, pw, lid, ts),
                )
                conn.commit()
                conn.close()
            await self._run(_do, user_id, email, password_hash, learner_id, now.isoformat())

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
            def _do(em):
                conn = self._get_conn()
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT user_id, email, password_hash, learner_id, is_active FROM users WHERE email = ?", (em,),
                ).fetchone()
                conn.close()
                if not row:
                    return None
                return dict(row)
            return await self._run(_do, email)

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
            def _do(uid):
                conn = self._get_conn()
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT user_id, email, password_hash, learner_id, is_active FROM users WHERE user_id = ?", (uid,),
                ).fetchone()
                conn.close()
                if not row:
                    return None
                return dict(row)
            return await self._run(_do, user_id)


learner_store = LearnerStore()
