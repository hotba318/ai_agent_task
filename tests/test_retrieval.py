import asyncio
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
import pytest
from pydantic import ValidationError

from group3.common.config import Settings
from group3.common.schemas import PaperDocument, RetrievalRequest, Section, canonical_arxiv_id
from group3.agents.retrieval.agent import RetrievalAgent
from group3.agents.retrieval.arxiv_client import ArxivClient, parse_feed
from group3.agents.retrieval.downloader import HttpTransport, RequestGate
from group3.agents.retrieval.fetcher import DocumentPipeline, FetchError
from group3.agents.retrieval.parser import parse_html, parse_tei
from group3.agents.retrieval.ranker import KeywordRanker
from group3.agents.retrieval.storage import JsonPaperStore


@pytest.mark.parametrize("values", [{"topic": " "}, {"target_papers": 0}, {"minimum_papers": 9}, {"task_id": "../escape"}])
def test_invalid_requests(values):
    base = {"task_id": "test", "topic": "multi agent systems"}
    with pytest.raises(ValidationError):
        RetrievalRequest(**(base | values))


def test_configuration(monkeypatch):
    monkeypatch.setenv("GROUP3_TARGET_PAPERS", "12")
    monkeypatch.setenv("GROUP3_MINIMUM_PAPERS", "10")
    assert Settings(_env_file=None).target_papers == 12
    with pytest.raises(ValidationError):
        Settings(download_delay_seconds=0)


def test_rank_relevance_then_freshness(make_paper):
    high_old = make_paper(1, year=2020)
    high_new = make_paper(2, year=2025)
    medium_new = make_paper(3, title="multi agent", year=2026)
    unrelated = make_paper(4, title="quantum optics", year=2026)
    ranked = KeywordRanker().rank("multi agent systems", [medium_new, unrelated, high_old, high_new, high_new])
    assert [p.paper_id for p in ranked] == [high_new.paper_id, high_old.paper_id, medium_new.paper_id]


@pytest.mark.parametrize("raw,expected", [("https://arxiv.org/abs/2401.12345v2", "arxiv:2401.12345"), ("hep-th/9901001v3", "arxiv:hep-th/9901001")])
def test_ids(raw, expected):
    assert canonical_arxiv_id(raw) == expected


def test_html_and_tei(html_body, tei_body):
    sections, refs = parse_html(html_body, "https://arxiv.org/html/2401.00001")
    assert [s.section_id for s in sections] == ["S1", "S1.S1"]
    assert "Nested" not in sections[0].text
    assert refs[0].doi == "10.1234/test"
    sections, refs = parse_tei(tei_body, "https://arxiv.org/pdf/2401.00001")
    assert sections[0].title == "Methods"
    assert refs[0].title == "Fixture title"
    assert refs[0].doi == "10.1234/test"
    with pytest.raises(ValueError):
        parse_html(b"<html>Access denied</html>", "https://arxiv.org")
    with pytest.raises(ValueError):
        parse_tei(b'<TEI xmlns="http://www.tei-c.org/ns/1.0"/>', "https://arxiv.org")


async def test_request_spacing_and_retry():
    now = [0.0]
    starts = []
    async def sleep(delay):
        now[0] += delay
    def handler(request):
        starts.append(now[0])
        return httpx.Response(503 if len(starts) == 1 else 200)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = HttpTransport(client, RequestGate(15, clock=lambda: now[0], sleep=sleep), retries=1, sleep=sleep)
        await transport.request("GET", "https://arxiv.org/html/test")
        await transport.request("GET", "https://arxiv.org/html/test2")
    assert starts == [0, 15, 30]


async def test_404_is_not_retried():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await HttpTransport(client, RequestGate(0)).request("GET", "https://arxiv.org/missing")
    assert len(calls) == 1


@pytest.mark.parametrize("html_ok,pdf_ok", [(True, True), (False, True), (False, False)])
async def test_document_paths(tmp_path, make_paper, html_body, tei_body, html_ok, pdf_ok):
    calls = []
    def handler(request):
        calls.append(request)
        if "/html/" in request.url.path:
            return httpx.Response(200 if html_ok else 404, content=html_body)
        if "/pdf/" in request.url.path:
            return httpx.Response(200, content=b"%PDF-fixture" if pdf_ok else b"denied")
        assert b'name="input"' in request.content
        return httpx.Response(200, content=tei_body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = HttpTransport(client, RequestGate(0), retries=0)
        fetcher = DocumentPipeline(transport, transport, "http://localhost:8070")
        if not html_ok and not pdf_ok:
            with pytest.raises(FetchError) as exc:
                await fetcher.fetch(make_paper(), tmp_path)
            assert len(exc.value.failures) == 2
            return
        document = await fetcher.fetch(make_paper(), tmp_path)
        assert Path(document.raw_document_path).exists()
        assert Path(document.parsed_document_path).exists()
        assert len(document.raw_sha256) == 64
        assert document.parse_method == ("arxiv_html" if html_ok else "grobid_pdf")
        assert bool(document.warnings) == (not html_ok)


@pytest.mark.parametrize("available,target,minimum,status", [(8,8,7,"completed"), (7,8,7,"completed"), (6,8,7,"insufficient_papers"), (3,3,3,"completed"), (5,5,5,"completed"), (12,12,10,"completed")])
async def test_counts_and_store(tmp_path, make_paper, available, target, minimum, status):
    class Search:
        async def search(self, topic, limit):
            assert limit == target * 3
            return [make_paper(i) for i in range(available)]
    class Fetch:
        async def fetch(self, paper, folder):
            return PaperDocument(**paper.model_dump(), parse_method="arxiv_html", raw_document_path="fixture", parsed_document_path="fixture", raw_sha256="f"*64,
                sections=[Section(section_id="s1", title="Fixture", text="Synthetic body", source_locator="/fixture", source_url=paper.html_url)], references=[])
    store = JsonPaperStore(tmp_path)
    agent = RetrievalAgent(Search(), KeywordRanker(), Fetch(), store, Settings())
    result = await agent.run(RetrievalRequest(task_id="counts", topic="multi agent systems", target_papers=target, minimum_papers=minimum))
    assert result.status == status
    assert result.selected_count == min(available, target)
    assert bool(result.warnings) == (available < target)
    folder = tmp_path / "counts" / result.run_id
    assert len(store.list_papers(folder)) == result.selected_count


async def test_failed_candidate_replaced_and_run_isolated(tmp_path, make_paper):
    class Search:
        async def search(self, topic, limit):
            return [make_paper(1), make_paper(2)]
    class Fetch:
        async def fetch(self, paper, folder):
            if paper.paper_id.endswith("00001"):
                raise ValueError("fixture parse failure")
            return PaperDocument(**paper.model_dump(), parse_method="arxiv_html", raw_document_path="fixture", parsed_document_path="fixture", raw_sha256="f"*64,
                sections=[Section(section_id="s1", title="Fixture", text="Synthetic body", source_locator="/fixture", source_url=paper.html_url)], references=[])
    agent = RetrievalAgent(Search(), KeywordRanker(), Fetch(), JsonPaperStore(tmp_path), Settings())
    request = RetrievalRequest(task_id="repeat", topic="multi agent systems", target_papers=1, minimum_papers=1)
    first, second = await agent.run(request), await agent.run(request)
    assert first.status == "completed" and len(first.failures) == 1
    assert first.run_id != second.run_id


async def test_search_failure_manifest(tmp_path):
    class Search:
        async def search(self, topic, limit):
            raise RuntimeError("fixture offline")
    result = await RetrievalAgent(Search(), KeywordRanker(), None, JsonPaperStore(tmp_path), Settings()).run(
        RetrievalRequest(task_id="offline", topic="test"))
    assert result.status == "failed" and result.selected_count == 0
    assert (tmp_path / "offline" / result.run_id / "manifest.json").exists()


async def test_arxiv_api_contract():
    feed = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2401.00001v2</id><title>Fixture title</title><summary>Fixture abstract</summary><published>2024-01-01T00:00:00Z</published><updated>2024-02-01T00:00:00Z</updated><author><name>Fixture Author</name></author></entry></feed>'''
    def handler(request):
        assert request.url.params["sortBy"] == "relevance"
        assert request.url.params["max_results"] == "9"
        assert request.url.params["search_query"] == 'all:"multi" AND all:"agent"'
        return httpx.Response(200, content=feed)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        papers = await ArxivClient(HttpTransport(client, RequestGate(0))).search("multi agent", 9)
    assert papers[0].paper_id == "arxiv:2401.00001"
    assert papers[0].submitted_date < papers[0].updated_date
    assert papers[0].version_id.endswith("v2")


def test_store_path_guard(tmp_path):
    with pytest.raises(ValueError):
        JsonPaperStore(tmp_path).begin("../escape", "run")


async def test_no_references_explicit_warning(tmp_path, make_paper):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=b'<section class="ltx_section"><h2>Actual heading</h2><p>Actual text</p></section>'))) as client:
        transport = HttpTransport(client, RequestGate(0), retries=0)
        document = await DocumentPipeline(transport, transport, "http://localhost:8070").fetch(make_paper(), tmp_path)
    assert document.references == []
    assert "No references extracted" in document.warnings[0]


async def test_grobid_unavailable_retains_both_failures(tmp_path, make_paper):
    def handler(request):
        if request.method == "POST":
            raise httpx.ConnectError("fixture GROBID offline", request=request)
        if "/html/" in request.url.path:
            return httpx.Response(404)
        return httpx.Response(200, content=b"%PDF-fixture")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = HttpTransport(client, RequestGate(0), retries=0)
        with pytest.raises(FetchError) as exc:
            await DocumentPipeline(transport, transport, "http://localhost:8070").fetch(make_paper(), tmp_path)
    assert [f.stage for f in exc.value.failures] == ["html", "pdf_grobid"]
    assert list(tmp_path.glob("*.pdf"))
    assert not list(tmp_path.glob("*.json"))


async def test_timeout_exhaustion():
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("fixture timeout", request=request)
    async def no_wait(seconds):
        pass
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="exhausted 3 attempts"):
            await HttpTransport(client, RequestGate(0), retries=2, sleep=no_wait).request("GET", "https://arxiv.org/test")
    assert len(calls) == 3


def test_arxiv_api_error_not_paper():
    feed = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#bad_query</id><summary>invalid query</summary></entry></feed>'''
    with pytest.raises(ValueError, match="arXiv API error"):
        parse_feed(feed)
