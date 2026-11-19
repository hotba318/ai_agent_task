import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

import connections_service
import reader_service
from evaluation import llm_judge
from group3_contracts import (
    Claim,
    ConnectionsRequest as Group3ConnectionsRequest,
    ConnectionsResult,
    Evidence,
    PaperDocument,
    ReaderAnalysis,
    ReaderResult,
    Section,
)
from paper_store import PaperStore
from schemas import (
    ClaimVerificationRequest,
    ConnectionsRequest,
    PaperStoreEntry,
    PaperTemplate,
    gemini_response_schema,
)


def make_paper(paper_id: str, method: str = "method") -> PaperTemplate:
    return PaperTemplate(
        paper_id=paper_id,
        title=f"Paper {paper_id}",
        core_problem="problem",
        proposed_method=method,
        datasets=["Dataset A"],
        key_findings=["finding"],
        limitations=[],
    )


class FakeModels:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    async def generate_content(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(parsed=self.response, text=None)


class FakeReader:
    async def extract_paper(
        self,
        paper_id: str,
        title: str,
        sections: list[str],
    ) -> PaperTemplate:
        assert title == "Stored title"
        assert sections == ["Abstract", "Results"]
        return make_paper(paper_id)

    async def verify_claim(
        self,
        request: ClaimVerificationRequest,
    ) -> SimpleNamespace:
        assert request.paper_text == "Abstract\n\nResults"
        return SimpleNamespace(
            verified=True,
            corrected_claim="claim",
            notes="supported",
        )


def make_group3_paper(paper_id: str, section_id: str, text: str) -> PaperDocument:
    return PaperDocument(
        paper_id=paper_id,
        version_id=f"{paper_id}v1",
        title=f"Paper {paper_id}",
        authors=["Test Author"],
        abstract="Test abstract",
        submitted_date="2025-01-01",
        updated_date="2025-01-02",
        source_url="https://arxiv.org/abs/2501.00001",
        html_url="https://arxiv.org/html/2501.00001",
        pdf_url="https://arxiv.org/pdf/2501.00001",
        parse_method="arxiv_html",
        raw_document_path="raw/paper.html",
        parsed_document_path="parsed/paper.json",
        raw_sha256="abc123",
        sections=[
            Section(
                section_id=section_id,
                title="Results",
                text=text,
                source_locator="section-1",
                source_url="https://arxiv.org/html/2501.00001#results",
            )
        ],
        references=[],
    )


class PaperReaderServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_and_verify_load_sections_from_store(self) -> None:
        store = PaperStore(":memory:")
        await store.save(
            "paper-1",
            PaperStoreEntry(
                title="Stored title",
                sections=["Abstract", "Results"],
            ),
        )
        previous_store = reader_service.paper_store
        previous_reader = reader_service.reader
        reader_service.paper_store = store
        reader_service.reader = FakeReader()
        try:
            transport = httpx.ASGITransport(app=reader_service.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://reader",
            ) as client:
                extracted = await client.post(
                    "/api/v1/extract",
                    json={"paper_id": "paper-1"},
                )
                verified = await client.post(
                    "/api/v1/verify",
                    json={
                        "paper_id": "paper-1",
                        "evidence": {
                            "claim": "claim",
                            "quote": "quote",
                            "section": "Results",
                        },
                    },
                )
            self.assertEqual(extracted.status_code, 200, extracted.text)
            self.assertEqual(verified.status_code, 200, verified.text)
            self.assertEqual(extracted.json()["paper_id"], "paper-1")
            self.assertTrue(verified.json()["verified"])
        finally:
            reader_service.paper_store = previous_store
            reader_service.reader = previous_reader
            await store.close()

    async def test_group3_read_returns_claims_with_verifiable_evidence(self) -> None:
        paper = make_group3_paper(
            "arxiv:2501.00001",
            "results",
            "The method improves accuracy by 5%.",
        )
        response = {
            "reader_result": {
                "paper_id": paper.paper_id,
                "results": [
                    {
                        "claim_id": "result-1",
                        "text": "The method improves accuracy by 5%.",
                        "evidence_ids": ["ev-1"],
                    }
                ],
            },
            "evidence": [
                {
                    "evidence_id": "ev-1",
                    "paper_id": paper.paper_id,
                    "section_id": "results",
                    "quote": "The method improves accuracy by 5%.",
                }
            ],
        }
        client = SimpleNamespace(
            aio=SimpleNamespace(models=FakeModels(response))
        )
        from paper_reader import GeminiPaperReader

        previous_reader = reader_service.reader
        reader_service.reader = GeminiPaperReader(client=client)
        try:
            transport = httpx.ASGITransport(app=reader_service.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://reader",
            ) as http_client:
                response = await http_client.post(
                    "/api/v1/group3/read",
                    json=paper.model_dump(mode="json"),
                )
            self.assertEqual(response.status_code, 200, response.text)
            result = ReaderAnalysis.model_validate(response.json())
            self.assertEqual(result.reader_result.results[0].evidence_ids, ["ev-1"])
        finally:
            reader_service.reader = previous_reader

    async def test_group3_reader_rejects_non_verbatim_quote(self) -> None:
        paper = make_group3_paper(
            "arxiv:2501.00001",
            "results",
            "The method improves accuracy by 5%.",
        )
        response = {
            "reader_result": {
                "paper_id": paper.paper_id,
                "results": [
                    {
                        "claim_id": "result-1",
                        "text": "The method improves accuracy by 10%.",
                        "evidence_ids": ["ev-1"],
                    }
                ],
            },
            "evidence": [
                {
                    "evidence_id": "ev-1",
                    "paper_id": paper.paper_id,
                    "section_id": "results",
                    "quote": "The method improves accuracy by 10%.",
                }
            ],
        }
        client = SimpleNamespace(
            aio=SimpleNamespace(models=FakeModels(response))
        )
        from paper_reader import GeminiPaperReader

        with self.assertRaisesRegex(ValueError, "exact source substring"):
            await GeminiPaperReader(client=client).analyze_group3(paper)


class ConnectionsAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_connections_with_unknown_paper_ids(self) -> None:
        response = {
            "relations": [
                {
                    "paper_ids": ["paper-1", "unknown"],
                    "relation_type": "shared_method",
                    "description": "shared",
                    "supporting_details": [],
                }
            ],
            "cross_paper_synthesis": "summary",
            "research_gaps": [],
        }
        client = SimpleNamespace(
            aio=SimpleNamespace(models=FakeModels(response))
        )
        agent = connections_service.GeminiConnectionsAgent(client=client)
        request = ConnectionsRequest(
            papers=[make_paper("paper-1"), make_paper("paper-2")]
        )
        with self.assertRaisesRegex(ValueError, "outside the request"):
            await agent.find_connections(request)

    async def test_group3_connections_match_writer_contract(self) -> None:
        request = Group3ConnectionsRequest(
            reader_results=[
                ReaderResult(
                    paper_id="paper-1",
                    methods=[
                        Claim(
                            claim_id="c1",
                            text="Uses method A.",
                            evidence_ids=["e1"],
                        )
                    ],
                ),
                ReaderResult(
                    paper_id="paper-2",
                    methods=[
                        Claim(
                            claim_id="c2",
                            text="Also uses method A.",
                            evidence_ids=["e2"],
                        )
                    ],
                ),
            ],
            evidence=[
                Evidence(
                    evidence_id="e1",
                    paper_id="paper-1",
                    section_id="methods",
                    quote="Method A",
                ),
                Evidence(
                    evidence_id="e2",
                    paper_id="paper-2",
                    section_id="methods",
                    quote="Method A",
                ),
            ],
        )
        response = {
            "connections": [
                {
                    "connection_id": "connection-1",
                    "kind": "similarity",
                    "claims": [
                        {
                            "claim_id": "shared-1",
                            "text": "Paper 1 uses method A.",
                            "evidence_ids": ["e1"],
                        },
                        {
                            "claim_id": "shared-2",
                            "text": "Paper 2 uses method A.",
                            "evidence_ids": ["e2"],
                        },
                    ],
                }
            ],
            "research_gaps": [],
        }
        client = SimpleNamespace(
            aio=SimpleNamespace(models=FakeModels(response))
        )
        previous_agent = connections_service.agent
        connections_service.agent = connections_service.GeminiConnectionsAgent(
            client=client
        )
        try:
            transport = httpx.ASGITransport(app=connections_service.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://connections",
            ) as http_client:
                response = await http_client.post(
                    "/api/v1/group3/connections",
                    json=request.model_dump(mode="json"),
                )
            self.assertEqual(response.status_code, 200, response.text)
            result = ConnectionsResult.model_validate(response.json())
            self.assertEqual(result.connections[0].kind, "similarity")
        finally:
            connections_service.agent = previous_agent


class GeminiSchemaTests(unittest.TestCase):
    def test_removes_gemini_unsupported_additional_properties(self) -> None:
        schema = gemini_response_schema(PaperTemplate)

        def contains_additional_properties(value: object) -> bool:
            if isinstance(value, dict):
                return "additionalProperties" in value or any(
                    contains_additional_properties(item)
                    for item in value.values()
                )
            if isinstance(value, list):
                return any(contains_additional_properties(item) for item in value)
            return False

        self.assertFalse(contains_additional_properties(schema))
        self.assertFalse(self._contains_const(schema))
        self.assertIn("properties", schema)
        self.assertIn("paper_id", schema["properties"])

    @staticmethod
    def _contains_const(value: object) -> bool:
        if isinstance(value, dict):
            return "const" in value or any(
                GeminiSchemaTests._contains_const(item)
                for item in value.values()
            )
        if isinstance(value, list):
            return any(GeminiSchemaTests._contains_const(item) for item in value)
        return False


class FakeJudgeClient:
    def __init__(self) -> None:
        response = {
            "accuracy": 4,
            "coverage": 4,
            "synthesis": 3,
            "evidence_quality": 4,
            "overall": 4,
            "rationale": "Reasoned score.",
            "missing_coverage": [],
            "unsupported_claims": [],
        }
        self.aio = SimpleNamespace(
            models=FakeModels(response),
            aclose=self.aclose,
        )

    async def aclose(self) -> None:
        return None


class EvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def test_topic_count_and_llm_judge_output(self) -> None:
        topics = json.loads(llm_judge.TOPICS_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(topics), 10)
        self.assertLessEqual(len(topics), 20)
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            reports_path = directory / "reports.json"
            reports_path.write_text(
                json.dumps(
                    {
                        "reports": [
                            {
                                "topic_id": "rag_retrieval",
                                "report": "Example review with citations.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            output_path = directory / "scores.json"
            with (
                patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}),
                patch.object(
                    llm_judge.genai,
                    "Client",
                    return_value=FakeJudgeClient(),
                ),
            ):
                result = await llm_judge.run_evaluation(
                    reports_path,
                    output_path,
                    "test-model",
                )
            self.assertEqual(result["topics_scored"], 1)
            self.assertEqual(result["average_scores"]["overall"], 4)
            saved = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["scores"][0]["topic_id"], "rag_retrieval")


if __name__ == "__main__":
    unittest.main()
