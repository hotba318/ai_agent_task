import os
from pathlib import Path

import aiosqlite
import httpx
from pydantic import ValidationError

from schemas import (
    ClaimEvidence,
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ExtractRequest,
    PaperTemplate,
    SupervisorReviewResult,
    TaskState,
)

MAX_RETRIES = 2


class ReaderServiceError(RuntimeError):
    pass


class SupervisorMemory:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = str(
            database_path or os.getenv("SUPERVISOR_DB_PATH", "supervisor_memory.sqlite3")
        )

    async def initialize(self) -> None:
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                CREATE TABLE IF NOT EXISTS task_states (
                    task_id TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            await database.commit()

    async def set_task_state(
        self,
        task_id: str,
        paper_id: str,
        status: str,
        retry_count: int,
        notes: str,
    ) -> None:
        await self.initialize()
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                INSERT INTO task_states (task_id, paper_id, status, retry_count, notes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    paper_id = excluded.paper_id,
                    status = excluded.status,
                    retry_count = excluded.retry_count,
                    notes = excluded.notes
                """,
                (task_id, paper_id, status, retry_count, notes),
            )
            await database.commit()

    async def get_task_state(self, task_id: str) -> TaskState | None:
        await self.initialize()
        async with aiosqlite.connect(self.database_path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(
                """
                SELECT task_id, paper_id, status, retry_count, notes
                FROM task_states WHERE task_id = ?
                """,
                (task_id,),
            )
            row = await cursor.fetchone()
        return TaskState.model_validate(dict(row)) if row is not None else None


class A2ASupervisorClient:
    def __init__(
        self,
        reader_service_url: str | None = None,
        memory: SupervisorMemory | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.reader_service_url = (
            reader_service_url
            or os.getenv("READER_SERVICE_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.memory = memory or SupervisorMemory()
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._owns_client = client is None

    async def __aenter__(self) -> "A2ASupervisorClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def extract_paper(self, request: ExtractRequest) -> PaperTemplate:
        try:
            response = await self._client.post(
                f"{self.reader_service_url}/api/v1/extract",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            return PaperTemplate.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise ReaderServiceError(f"Reader extraction request failed: {error}") from error

    async def verify_claim(
        self,
        request: ClaimVerificationRequest,
    ) -> ClaimVerificationResult:
        try:
            response = await self._client.post(
                f"{self.reader_service_url}/api/v1/verify",
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            return ClaimVerificationResult.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise ReaderServiceError(f"Reader verification request failed: {error}") from error

    async def review_paper(
        self,
        task_id: str,
        extract_request: ExtractRequest,
        evidence_items: list[ClaimEvidence],
    ) -> SupervisorReviewResult:
        paper_id = extract_request.paper_id
        await self.memory.set_task_state(
            task_id, paper_id, "Running", retry_count=0, notes=""
        )
        retry_count = 0
        try:
            paper = await self.extract_paper(extract_request)
            paper_text = "\n\n".join(extract_request.sections)
            verifications: list[ClaimVerificationResult] = []

            for evidence in evidence_items:
                request = ClaimVerificationRequest(
                    paper_id=paper_id,
                    evidence=evidence,
                    paper_text=paper_text,
                )
                result = await self.verify_claim(request)
                verifications.append(result)
                retries_for_claim = 0
                while not result.verified and retries_for_claim < MAX_RETRIES:
                    retries_for_claim += 1
                    retry_count += 1
                    result = await self.verify_claim(request)
                    verifications[-1] = result

                if not result.verified:
                    note = (
                        f"Evidence for claim {evidence.claim!r} remained "
                        f"unverified after {retries_for_claim} retries: {result.notes}"
                    )
                    await self.memory.set_task_state(
                        task_id,
                        paper_id,
                        "Unable to Verify",
                        retry_count=retry_count,
                        notes=note,
                    )
                    return SupervisorReviewResult(
                        paper=paper,
                        verifications=verifications,
                        status="Unable to Verify",
                        retry_count=retry_count,
                    )

            await self.memory.set_task_state(
                task_id,
                paper_id,
                "Completed",
                retry_count=retry_count,
                notes="All submitted evidence was verified.",
            )
            return SupervisorReviewResult(
                paper=paper,
                verifications=verifications,
                status="Completed",
                retry_count=retry_count,
            )
        except ReaderServiceError as error:
            await self.memory.set_task_state(
                task_id,
                paper_id,
                "Failed",
                retry_count=retry_count,
                notes=str(error),
            )
            raise
