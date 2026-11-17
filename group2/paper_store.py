import asyncio
import json
import os
from pathlib import Path

import aiosqlite

from schemas import PaperStoreEntry


class PaperNotFoundError(LookupError):
    pass


class PaperStore:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(
            database_path or os.getenv("PAPER_STORE_DB_PATH", "paper_store.sqlite3")
        )
        self._database: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._lock:
            if self._database is not None:
                return
            if self.database_path != ":memory:":
                Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
            self._database = await aiosqlite.connect(self.database_path)
            self._database.row_factory = aiosqlite.Row
            await self._database.execute(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    sections_json TEXT NOT NULL
                )
                """
            )
            await self._database.commit()

    async def save(self, paper_id: str, entry: PaperStoreEntry) -> None:
        await self.initialize()
        async with self._lock:
            if self._database is None:
                raise RuntimeError("Paper store was not initialized.")
            await self._database.execute(
                """
                INSERT INTO papers (paper_id, title, sections_json)
                VALUES (?, ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                    title = excluded.title,
                    sections_json = excluded.sections_json
                """,
                (paper_id, entry.title, json.dumps(entry.sections)),
            )
            await self._database.commit()

    async def get(self, paper_id: str) -> PaperStoreEntry:
        await self.initialize()
        async with self._lock:
            if self._database is None:
                raise RuntimeError("Paper store was not initialized.")
            cursor = await self._database.execute(
                "SELECT title, sections_json FROM papers WHERE paper_id = ?",
                (paper_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise PaperNotFoundError(f"Paper {paper_id!r} is not in the paper store.")
        return PaperStoreEntry(
            title=row["title"],
            sections=json.loads(row["sections_json"]),
        )

    async def close(self) -> None:
        async with self._lock:
            if self._database is not None:
                await self._database.close()
                self._database = None
