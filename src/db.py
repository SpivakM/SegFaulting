"""Async SQLite session store for FileFlow."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.environ.get("FILEFLOW_DB", os.path.join(_BASE_DIR, "fileflow.db"))
_SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours


async def init_db() -> None:
    """Create the sessions table if it does not exist."""
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                metadata   TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        await db.commit()
    logger.info("Database initialised at %s", _DB_PATH)


async def create_session(session_id: str, metadata: dict[str, Any]) -> None:
    """Persist a new session with the given metadata."""
    now = datetime.now(timezone.utc).timestamp()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (id, metadata, created_at) VALUES (?, ?, ?)",
            (session_id, json.dumps(metadata), now),
        )
        await db.commit()


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Return the metadata dict for *session_id*, or None if not found."""
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            "SELECT metadata FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    return json.loads(row[0])


async def update_session(session_id: str, updates: dict[str, Any]) -> None:
    """Merge *updates* into an existing session's metadata."""
    current = await get_session(session_id)
    if current is None:
        return
    current.update(updates)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET metadata = ? WHERE id = ?",
            (json.dumps(current), session_id),
        )
        await db.commit()


async def purge_expired_sessions() -> None:
    """Delete sessions (and their associated files) older than TTL."""
    cutoff = datetime.now(timezone.utc).timestamp() - _SESSION_TTL_SECONDS
    async with aiosqlite.connect(_DB_PATH) as db:
        async with db.execute(
            "SELECT id, metadata FROM sessions WHERE created_at < ?", (cutoff,)
        ) as cursor:
            rows = await cursor.fetchall()
        for _, meta_json in rows:
            meta = json.loads(meta_json)
            for key in ("path", "data_path"):
                path = meta.get(key)
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError as exc:
                        logger.warning("Could not remove stale file %s: %s", path, exc)
        if rows:
            await db.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
            await db.commit()
            logger.info("Purged %d expired sessions", len(rows))
