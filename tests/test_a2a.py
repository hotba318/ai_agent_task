import asyncio
from uuid import uuid4

import httpx
import pytest

from group3.a2a.server import create_app
from group3.common.schemas import RetrievalResult
from tests.test_writer import writer_input


def rpc(operation, payload, *, request_id="1"):
    return {"jsonrpc": "2.0", "id": request_id, "method": "message/send", "params": {
        "message": {"kind": "message", "messageId": uuid4().hex, "role": "user", "parts": [
            {"kind": "data", "data": {"operation": operation, "payload": payload}}]}, "configuration": {"blocking": True}}}


def artifact(task, name="result.json"):
    return next(a for a in task["artifacts"] if a["name"] == name)["parts"][0]["data"]


@pytest.mark.parametrize("agent", ["retrieval", "references", "writer"])
async def test_agent_cards(agent):
    app = create_app(agent, "http://test/")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        result = await client.get("/.well-known/agent-card.json")
    assert result.status_code == 200
    assert result.json()["protocolVersion"] == "0.3.0"
    assert result.json()["skills"][0]["id"] == agent


async def test_writer_a2a_artifacts_task_get_and_revision(tmp_path, monkeypatch, writer_input):
    monkeypatch.setenv("GROUP3_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("GROUP3_WRITER_MODE", "extractive")
    app = create_app("writer", "http://test/")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json=rpc("write", writer_input.model_dump(mode="json")))
        body = response.json()
        assert "error" not in body, body
        task = body["result"]
        assert task["status"]["state"] == "completed", task
        result = artifact(task)
        assert result["status"] == "needs_review" and not result["evidence_verified"]
        assert any(a["name"] == "report.md" for a in task["artifacts"])
        fetched = await client.post("/", json={"jsonrpc":"2.0","id":"get","method":"tasks/get","params":{"id":task["id"]}})
        assert fetched.json()["result"]["id"] == task["id"]
        revision = {"report_id": result["report_id"], "feedback": {"missing_sections": ["limitations"], "note": "Keep both sides"}}
        revised = (await client.post("/", json=rpc("revise", revision))).json()["result"]
        assert artifact(revised)["revision"] == 1
        rejected = (await client.post("/", json=rpc("revise", revision))).json()["result"]
        assert rejected["status"]["state"] == "failed"
        assert artifact(rejected, "error.json")["error"]["code"] == "revision_limit"


async def test_missing_writer_input_required(tmp_path, monkeypatch, writer_input):
    monkeypatch.setenv("GROUP3_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("GROUP3_WRITER_MODE", "extractive")
    writer_input.reader_results = []
    writer_input.research_gaps = []
    writer_input.connections = []
    app = create_app("writer", "http://test/")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        task = (await client.post("/", json=rpc("write", writer_input.model_dump(mode="json")))).json()["result"]
    assert task["status"]["state"] == "input-required"
    assert artifact(task)["missing_coverage"]


async def test_input_required_task_continuation(tmp_path, monkeypatch, writer_input):
    monkeypatch.setenv("GROUP3_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("GROUP3_WRITER_MODE", "extractive")
    writer_input.research_gaps = []
    app = create_app("writer", "http://test/")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        first = (await client.post("/",json=rpc("write",writer_input.model_dump(mode="json")))).json()["result"]
        request = rpc("revise",{"report_id":artifact(first)["report_id"],"feedback":{"missing_sections":["research_gaps"]}})
        request["params"]["message"].update({"taskId":first["id"],"contextId":first["contextId"]})
        continued = (await client.post("/",json=request)).json()["result"]
    assert continued["id"] == first["id"]
    assert continued["status"]["state"] == "input-required"
    latest = [a["parts"][0]["data"] for a in continued["artifacts"] if a["name"] == "result.json"][-1]
    assert latest["revision"] == 1


@pytest.mark.parametrize("mode", ["invalid", "timeout", "secret_error"])
async def test_errors(mode):
    async def handler(agent, operation, payload):
        if mode == "invalid":
            raise ValueError("malformed input")
        if mode == "timeout":
            await asyncio.sleep(1)
        raise RuntimeError("Bearer sensitive-token-fixture")
    app = create_app("references", "http://test/", handler=handler, timeout=.01)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json=rpc("references", {}))
    task = response.json()["result"]
    assert task["status"]["state"] == "failed"
    assert artifact(task,"error.json")["error"]["code"] == {"invalid":"invalid_input","timeout":"timeout","secret_error":"execution_error"}[mode]
    assert "sensitive-token-fixture" not in response.text


async def test_retrieval_partial_result():
    async def handler(agent, operation, payload):
        return RetrievalResult(task_id="fixture", run_id="run", status="insufficient_papers", requested_count=8, selected_count=0, paper_store_uri="file:///fixture", paper_ids=[])
    app = create_app("retrieval", "http://test/", handler=handler)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        task = (await client.post("/",json=rpc("retrieve",{}))).json()["result"]
    assert task["status"]["state"] == "input-required"
    assert artifact(task)["status"] == "insufficient_papers"


async def test_missing_store_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("GROUP3_STORE_ROOT", str(tmp_path))
    app = create_app("references", "http://test/")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        task = (await client.post("/", json=rpc("references", {"task_id":"missing", "run_id":"missing"}))).json()["result"]
    assert artifact(task, "error.json")["error"]["code"] == "not_found"


async def test_ambiguous_references_request_review(make_paper):
    from group3.agents.references.agent import CommonReferencesAgent
    from tests.test_references import document,reference
    papers=[document(make_paper(1),[reference(doi="10.1234/a",arxiv_id="2401.99999")]),
        document(make_paper(2),[reference(doi="10.1234/b",arxiv_id="2401.99999")])]
    async def handler(agent,operation,payload):
        return CommonReferencesAgent().analyze(papers,"test")
    app=create_app("references","http://test/",handler=handler)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
        task=(await client.post("/",json=rpc("references",{}))).json()["result"]
    assert task["status"]["state"]=="input-required"
    assert artifact(task)["review_required"]
