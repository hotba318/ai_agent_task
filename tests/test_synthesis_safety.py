import json
import time
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from group3.agents.writer.agent import WriterAgent
from group3.agents.writer.draft import Statement, SupportReview, SupportAssessment, validate_draft
from group3.agents.writer.planner import GroqPlanner
from group3.common.llm import TokenBudget, structured_completion
from group3.agents.retrieval.planner import ModelSearchDecision
from tests.test_writer import writer_input
from tests.synthesis_fixtures import mock_draft, supported_review


def test_cli_accepts_powershell_utf8_bom(tmp_path,writer_input,monkeypatch):
    from group3.analysis_cli import main
    source=tmp_path/"input.json"
    source.write_text(writer_input.model_dump_json(),encoding="utf-8-sig")
    output=tmp_path/"result.json"
    monkeypatch.setattr("sys.argv",["group3.analysis_cli","write","--input",str(source),"--mode","extractive",
        "--output-root",str(tmp_path/"reports"),"--result",str(output)])
    assert main()==0
    result=json.loads(output.read_text(encoding="utf-8"))
    assert Path(result["markdown_path"]).is_file() and result["model_calls"]==0


async def test_provider_invalid_json_has_one_repair(tmp_path,writer_input):
    calls=[]
    def handler(request):
        name=json.loads(request.content)["response_format"]["json_schema"]["name"]
        calls.append(name)
        if len(calls)==1:
            return httpx.Response(400,json={"error":{"code":"json_validate_failed","message":"fixture"}})
        draft=mock_draft(writer_input)
        output=draft if name=="grounded_literature_draft" else supported_review(draft)
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)
    assert result.model_calls==3
    assert len(calls)==3


async def test_no_grounded_claims_means_no_model_call(tmp_path,writer_input):
    writer_input.reader_results=[]
    writer_input.research_gaps=[]
    writer_input.connections=[]
    def handler(request):
        raise AssertionError("No model call should be made")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)
    assert result.model_calls==0 and result.status=="coverage_incomplete"
    assert "근거로 작성·검토를 통과한 문장이 없습니다" in result.markdown


async def test_repeated_unsupported_number_is_withheld_and_audited(tmp_path,writer_input):
    draft=mock_draft(writer_input)
    draft.introduction[0].text="성능이 987654321.123% 향상되었다."
    def handler(request):
        payload=json.loads(request.content)
        name=payload["response_format"]["json_schema"]["name"]
        output=draft
        if name=="grounded_support_review":
            values=json.loads(payload["messages"][-1]["content"])["draft"]["statements"]
            output=SupportReview(assessments=[SupportAssessment(statement_id=s["statement_id"],verdict="supported",reason="fixture") for s in values])
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)
    assert "987654321.123" not in result.markdown
    assert result.status=="coverage_incomplete"
    audit=json.loads(Path(result.decisions_path).read_text(encoding="utf-8"))
    assert "987654321.123" in json.dumps(audit)
    assert any(v.startswith("programmatic_review:") for v in result.missing_coverage)


def test_conflict_cannot_be_summarized_from_one_side(writer_input):
    draft=mock_draft(writer_input)
    draft.connections[0].claim_ids=["conflict-a"]
    with pytest.raises(ValueError,match="both sides"):
        validate_draft(draft,writer_input)


async def test_batched_review_requires_exact_statement_coverage(tmp_path,writer_input):
    draft=mock_draft(writer_input)
    for i in range(4):
        draft.paper_summaries[0].paragraphs.append(Statement(statement_id=f"extra-{i}",text="추가 요약입니다.",
            claim_ids=[writer_input.reader_results[0].overview[0].claim_id],kind="supported"))
    batches=[]
    def handler(request):
        payload=json.loads(request.content)
        name=payload["response_format"]["json_schema"]["name"]
        output=draft
        if name=="grounded_support_review":
            values=json.loads(payload["messages"][-1]["content"])["draft"]["statements"]
            batches.append(len(values))
            output=SupportReview(assessments=[SupportAssessment(statement_id=s["statement_id"],verdict="supported",reason="fixture") for s in values])
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)
    assert batches==[8,3] and result.model_calls==3


async def test_reviewer_omitting_statement_is_not_accepted(tmp_path,writer_input):
    draft=mock_draft(writer_input)
    def handler(request):
        name=json.loads(request.content)["response_format"]["json_schema"]["name"]
        output=draft if name=="grounded_literature_draft" else SupportReview(assessments=[])
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError,match="batch statement"):
            await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)
    assert not list(tmp_path.glob("*/revision-*/report.md"))


async def test_duplicate_quote_payload_is_compact_without_losing_evidence(tmp_path,writer_input):
    writer_input.reader_results[0].overview[0].text=writer_input.evidence[0].quote
    def handler(request):
        payload=json.loads(request.content)
        name=payload["response_format"]["json_schema"]["name"]
        if name=="grounded_literature_draft":
            source=json.loads(payload["messages"][-1]["content"])
            claim=next(c for c in source["claims"] if c["claim_id"]==writer_input.reader_results[0].overview[0].claim_id)
            assert claim["text"].startswith("Verbatim source excerpt")
            assert next(e for e in source["evidence"] if e["evidence_id"]==writer_input.evidence[0].evidence_id)["quote"]==writer_input.evidence[0].quote
        draft=mock_draft(writer_input)
        output=draft if name=="grounded_literature_draft" else supported_review(draft)
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)


async def test_budget_obeys_provider_reset(monkeypatch):
    waits=[]
    async def fake_wait(seconds):
        waits.append(seconds)
    monkeypatch.setattr("group3.common.llm.wait_in_chunks",fake_wait)
    budget=TokenBudget()
    budget.observe({"x-ratelimit-remaining-tokens":"10","x-ratelimit-reset-tokens":"1m2s"})
    await budget.wait(100)
    assert len(waits)==1 and 62<waits[0]<=63
    assert budget.waits==1 and budget.remaining is None


async def test_transport_error_does_not_expose_credentials():
    def handler(request):
        raise httpx.ConnectError("Bearer fixture-secret-value",request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError) as exc:
            await structured_completion(client,SecretStr("fixture-secret-value"),"openai/gpt-oss-20b",ModelSearchDecision,[],name="fixture")
    assert "fixture-secret-value" not in str(exc.value)
    assert exc.value.__suppress_context__


async def test_rate_limit_waits_once_and_uses_only_server_delay(monkeypatch):
    waits,calls=[],[]
    async def fake_wait(seconds):
        waits.append(seconds)
    monkeypatch.setattr("group3.common.llm.wait_in_chunks",fake_wait)
    def handler(request):
        calls.append(request)
        if len(calls)==1:
            return httpx.Response(429,headers={"Retry-After":"10"})
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":json.dumps({"action":"stop","query":"topic","reason":"fixture"})}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await structured_completion(client,SecretStr("fixture"),"openai/gpt-oss-20b",ModelSearchDecision,[],name="fixture")
    assert len(calls)==2 and waits==[11]
