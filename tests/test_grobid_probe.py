from pathlib import Path

import httpx
import pytest

from group3.agents.retrieval.downloader import HttpTransport, RequestGate
from group3.agents.retrieval.fetcher import DocumentPipeline
from group3.common.config import Settings
from group3.integration.grobid_probe import verify_grobid
from tests.test_integration_handoff import local_store


@pytest.mark.parametrize("pdf_ok", [True, False])
async def test_pdf_preference_has_no_fabricated_html_failure(tmp_path, make_paper, html_body, tei_body, pdf_ok):
    calls = []
    def handler(request):
        calls.append(request)
        if "/pdf/" in request.url.path:
            return httpx.Response(200,content=b"%PDF-fixture" if pdf_ok else b"not PDF")
        if request.method == "POST":
            assert b'name="consolidateHeader"' in request.content
            return httpx.Response(200,content=tei_body)
        return httpx.Response(200,content=html_body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        transport = HttpTransport(client,RequestGate(0),retries=0)
        doc = await DocumentPipeline(transport,transport,"http://grobid.test",preferred_format="pdf").fetch(make_paper(),tmp_path)
    assert "/pdf/" in calls[0].url.path
    assert doc.parse_method == ("grobid_pdf" if pdf_ok else "arxiv_html")
    if pdf_ok:
        assert not doc.warnings
        assert not any("/html/" in call.url.path for call in calls)
    else:
        assert "pdf_grobid" in doc.warnings[0]


@pytest.mark.parametrize("scenario", ["success", "not_alive", "bad_pdf", "unavailable_grobid"])
async def test_probe_records_success_and_failures(local_store, html_body, tei_body, scenario):
    store,papers,selection = local_store
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/api/isalive"):
            return httpx.Response(200,text="false" if scenario == "not_alive" else "true")
        if request.url.path.endswith("/api/version"):
            return httpx.Response(200,json={"version":"test-version"})
        if "/pdf/" in request.url.path:
            return httpx.Response(200,content=b"bad" if scenario == "bad_pdf" else b"%PDF-fixture")
        if request.method == "POST":
            return httpx.Response(503 if scenario == "unavailable_grobid" else 200,content=tei_body)
        return httpx.Response(200,content=html_body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        record = await verify_grobid(Settings(_env_file=None,store_root=store.root),selection,papers[0].paper_id,
            "http://grobid.test",client=client)
    assert record["success"] == (scenario == "success")
    assert record["post_attempts"] == sum(c.method == "POST" for c in calls)
    assert record["post_attempts"] <= 1
    assert record["source_store_modified"] is False
    assert record["retrieval"]["status"] == ("completed" if scenario == "success" else "failed")
    if scenario == "success":
        assert Path(record["raw_document_path"]).read_bytes().startswith(b"%PDF-")
        assert record["raw_sha256_verified"] and record["sections"] and record["references"]
        assert Path(record["tei_path"]).suffix == ".xml"
    else:
        assert record.get("tei_path") is None


async def test_probe_rejects_unknown_paper_before_network(local_store):
    store,_,selection=local_store
    calls=[]
    def handler(request):
        calls.append(request)
        raise AssertionError("must not make external requests")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError,match="not in the selected"):
            await verify_grobid(Settings(_env_file=None,store_root=store.root),selection,"arxiv:2401.99999","http://grobid.test",client=client)
    assert calls == []


@pytest.mark.parametrize("url", ["http://user:password@grobid.test", "https://grobid.test/?token=secret", "file:///tmp/grobid"])
async def test_probe_rejects_unsafe_service_url(local_store,url):
    store,papers,selection=local_store
    with pytest.raises(ValueError,match="plain HTTP"):
        await verify_grobid(Settings(_env_file=None,store_root=store.root),selection,papers[0].paper_id,url)


def test_invalid_preference_and_setting():
    from pydantic import ValidationError
    with pytest.raises(ValueError,match="preferred_format"):
        DocumentPipeline(None,None,"http://grobid.test",preferred_format="unknown")
    with pytest.raises(ValidationError):
        Settings(_env_file=None,preferred_format="unknown")
