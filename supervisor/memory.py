from datetime import UTC, datetime
from pathlib import Path
import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    task_id     TEXT PRIMARY KEY NOT NULL,
    topic       TEXT NOT NULL,
    status      TEXT NOT NULL,
    report_id   TEXT,
    revision    INTEGER,
    started_at  TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS steps (
    task_id     TEXT NOT NULL,
    step        TEXT NOT NULL,
    item        TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 1,
    notes       TEXT NOT NULL DEFAULT '',
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (task_id, step, item)
);
"""

def _now() -> str:
    """The current time in UTC as ISO 8601 text, for example 2026-11-16T10:02:11+00:00."""
    return datetime.now(UTC).isoformat(timespec='seconds')


class RunMemory:
    """The supervisor's memory: one row per run, one row per step or item of a run."""

    def __init__(self, path: Path) -> None:
        self.path = path

    async def create_tables(self) -> None:
        """Create the database file and both tables if they do not exist yet."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def start_run(self, task_id: str, topic: str) -> None:
        """Record a new run as running."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                'INSERT INTO runs (task_id, topic, status, started_at) VALUES (?, ?, ?, ?)',
                (task_id, topic, 'running', _now()),
            )
            await db.commit()

    async def record_step(
        self, task_id: str, step: str, status: str, item: str = '', notes: str = '', retry: bool = False,
    ) -> None:
        """Record the status of a step or of one item in it; a retry counts one more attempt."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO steps (task_id, step, item, status, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (task_id, step, item) DO UPDATE SET
                    status = excluded.status,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at,
                    attempts = steps.attempts + ?
                """,
                (task_id, step, item, status, notes, _now(), 1 if retry else 0),
            )
            await db.commit()

    async def finish_run(self, task_id: str, status: str, report_id: str | None = None, revision: int | None = None) -> None:
        """Record how a run ended, and which report it produced."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                'UPDATE runs SET status = ?, report_id = ?, revision = ?, finished_at = ? WHERE task_id = ?',
                (status, report_id, revision, _now(), task_id),
            )
            await db.commit()
            