import asyncio
import json
from pathlib import Path

import httpx
import pytest

from group3.common.analysis_schemas import Claim, Connection, CoverageFeedback, Evidence, ReaderResult, RevisionRequest, WriterRequest
from group3.agents.references.agent import CommonReferencesAgent
from group3.agents.writer.agent import WriterAgent
from group3.agents.writer.planner import ExtractivePlanner, GroqPlanner, ReportPlan, permitted_plan
from group3.agents.writer.state import RevisionLimitError
from group3.agents.writer.validator import validate_input
from tests.test_references import document, reference
from tests.synthesis_fixtures import mock_draft, supported_review


@pytest.fixture
def writer_input(make_paper):
    papers = [document(make_paper(i), [reference(doi="10.1234/a")]) for i in (1,2)]
    readers, evidence = [], []
    for index, paper in enumerate(papers):
        fields = {}
        for name in ("overview", "methods", "datasets", "results", "limitations"):
            eid = f"e-{index}-{name}"
            evidence.append(Evidence(evidence_id=eid, paper_id=paper.paper_id, section_id="s1", quote="Synthetic evidence body"))
            fields[name] = [Claim(claim_id=f"c-{index}-{name}", text=f"Synthetic {name} fixture", evidence_ids=[eid])]
        readers.append(ReaderResult(paper_id=paper.paper_id, **fields))
    connection = Connection(connection_id="fixture-conflict", kind="conflict", claims=[
        Claim(claim_id="conflict-a", text="Synthetic side A", evidence_ids=[evidence[0].evidence_id]),
        Claim(claim_id="conflict-b", text="Synthetic side B", evidence_ids=[evidence[5].evidence_id])])
    return WriterRequest(task_id="test", topic="Fixture topic", papers=papers, reader_results=readers, evidence=evidence,
        common_references=CommonReferencesAgent().analyze(papers, "test"), connections=[connection],
        research_gaps=[Claim(claim_id="gap", text="Synthetic gap fixture", evidence_ids=[evidence[0].evidence_id])], data_provenance="example_fixture")


async def test_markdown_and_source_map(tmp_path, writer_input):
    result = await WriterAgent(ExtractivePlanner(), tmp_path).run(writer_input)
    assert result.status == "needs_review" and not result.evidence_verified
    md = Path(result.markdown_path).read_text(encoding="utf-8")
    assert sum(line.startswith("## ") for line in md.splitlines()) == 8
    assert "Synthetic side A" in md and "Synthetic side B" in md
    assert "예시 데이터" in md and "검증 대기" in md
    block = md.split("| 논문 |", 1)[1].split("\n\n", 1)[0]
    assert len(block.splitlines()) == 4  # header, separator, both data rows; no blank lines
    evidence = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert len(evidence["evidence"]) == 10
    assert all(e.evidence_id in md for e in writer_input.evidence)


async def test_missing_inputs_no_fabrication(tmp_path, writer_input):
    request = writer_input.model_copy(update={"reader_results": [], "connections": [], "research_gaps": []})
    result = await WriterAgent(ExtractivePlanner(), tmp_path).run(request)
    assert result.status == "coverage_incomplete"
    assert "connections" in result.missing_coverage
    assert "Synthetic methods fixture" not in result.markdown
    assert "Reader 입력이 없습니다" in result.markdown


@pytest.mark.parametrize("corruption", ["unknown_paper", "unknown_section", "bad_quote", "unknown_evidence", "foreign_reader_evidence", "one_sided_conflict", "fake_reference", "fake_reference_title", "duplicate_claim"])
def test_invalid_evidence_rejected(writer_input, corruption):
    request = writer_input.model_copy(deep=True)
    if corruption == "unknown_paper":
        request.evidence[0].paper_id = "arxiv:2401.99999"
    elif corruption == "unknown_section":
        request.evidence[0].section_id = "invented"
    elif corruption == "bad_quote":
        request.evidence[0].quote = "not present in supplied section"
    elif corruption == "unknown_evidence":
        request.reader_results[0].methods[0].evidence_ids = ["invented"]
    elif corruption == "foreign_reader_evidence":
        request.reader_results[0].methods[0].evidence_ids = [request.evidence[-1].evidence_id]
    elif corruption == "one_sided_conflict":
        request.connections[0].claims = request.connections[0].claims[:1]
    elif corruption == "fake_reference":
        request.common_references.common_references[0].occurrences[0].raw_text = "invented citation"
    elif corruption == "fake_reference_title":
        request.common_references.common_references[0].title = "Invented title not in original reference"
    else:
        request.research_gaps[0].claim_id = request.reader_results[0].overview[0].claim_id
    with pytest.raises(ValueError):
        validate_input(request)


async def test_coverage_once_persisted(tmp_path, writer_input):
    first = await WriterAgent(ExtractivePlanner(), tmp_path).run(writer_input)
    revision = RevisionRequest(report_id=first.report_id, feedback=CoverageFeedback(missing_sections=["limitations"], note="Show source details"))
    result = await WriterAgent(ExtractivePlanner(), tmp_path).revise(revision)
    assert result.revision == 1 and "Show source details" in result.markdown
    assert Path(first.markdown_path).exists()  # revision 0 is preserved
    with pytest.raises(RevisionLimitError):
        await WriterAgent(ExtractivePlanner(), tmp_path).revise(revision)


async def test_rewrite_cannot_fill_missing_evidence(tmp_path, writer_input):
    writer_input.research_gaps = []
    agent = WriterAgent(ExtractivePlanner(), tmp_path)
    first = await agent.run(writer_input)
    result = await agent.revise(RevisionRequest(report_id=first.report_id, feedback=CoverageFeedback(missing_sections=["research_gaps"])))
    assert result.status == "coverage_incomplete" and "research_gaps" in result.missing_coverage


async def test_revision_with_corrected_group2_input(tmp_path, writer_input):
    incomplete = writer_input.model_copy(deep=True)
    incomplete.research_gaps = []
    agent = WriterAgent(ExtractivePlanner(), tmp_path)
    first = await agent.run(incomplete)
    result = await agent.revise(RevisionRequest(report_id=first.report_id,
        feedback=CoverageFeedback(missing_sections=["research_gaps"]), updated_input=writer_input))
    assert result.status == "needs_review"
    assert "Synthetic gap fixture" in result.markdown


async def test_revision_cannot_replace_source_papers(tmp_path, writer_input):
    agent = WriterAgent(ExtractivePlanner(), tmp_path)
    first = await agent.run(writer_input)
    changed = writer_input.model_copy(deep=True)
    changed.papers[0].title = "Changed source"
    with pytest.raises(ValueError, match="preserve original"):
        await agent.revise(RevisionRequest(report_id=first.report_id, feedback=CoverageFeedback(), updated_input=changed))


async def test_concurrent_revisions_reserve_once(tmp_path, writer_input):
    agent = WriterAgent(ExtractivePlanner(), tmp_path)
    first = await agent.run(writer_input)
    revision = RevisionRequest(report_id=first.report_id, feedback=CoverageFeedback())
    results = await asyncio.gather(agent.revise(revision), agent.revise(revision), return_exceptions=True)
    assert sum(isinstance(r, RevisionLimitError) for r in results) == 1
    assert sum(not isinstance(r, Exception) for r in results) == 1


async def test_markup_escaped(tmp_path, writer_input):
    writer_input.reader_results[0].overview[0].text = "<script>x</script> [fake](https://fake.invalid) | break"
    result = await WriterAgent(ExtractivePlanner(), tmp_path).run(writer_input)
    assert "<script>" not in result.markdown
    assert "\\[fake\\]" in result.markdown and "\\| break" in result.markdown


@pytest.mark.parametrize("malicious", [False, True])
async def test_groq_contract_mock(tmp_path, writer_input, malicious):
    def handler(request):
        data = json.loads(request.content)
        assert request.url.host == "api.groq.com"
        assert data["model"] == "openai/gpt-oss-20b"
        assert data["response_format"]["json_schema"]["strict"] is True
        draft=mock_draft(writer_input)
        if malicious:
            draft.research_gaps[0].claim_ids=["invented-claim"]
        name=data["response_format"]["json_schema"]["name"]
        output=draft if name=="grounded_literature_draft" else supported_review(draft)
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        agent = WriterAgent(GroqPlanner(client, "test-secret-not-real"), tmp_path)
        if malicious:
            with pytest.raises(ValueError, match="must cite supplied claims"):
                await agent.run(writer_input)
            assert not list(tmp_path.glob("*/revision-*/report.md"))
        else:
            result = await agent.run(writer_input)
            assert result.mode == "groq" and "근거를 종합한 초안" in result.markdown
            assert "test-secret-not-real" not in result.model_dump_json()


def test_groq_key_required():
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        GroqPlanner(None, "")
