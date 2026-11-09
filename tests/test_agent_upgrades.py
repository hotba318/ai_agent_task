import json
from pathlib import Path

import httpx
import pytest

from group3.agents.retrieval.agent import RetrievalAgent
from group3.agents.retrieval.planner import GroqRetrievalPlanner, SearchObservation
from group3.agents.retrieval.ranker import KeywordRanker
from group3.agents.retrieval.storage import JsonPaperStore
from group3.agents.writer.agent import WriterAgent
from group3.agents.writer.draft import Statement, validate_draft
from group3.agents.writer.planner import GroqPlanner
from group3.agents.writer.state import RevisionLimitError
from group3.common.analysis_schemas import CoverageFeedback, RevisionRequest
from group3.common.config import Settings
from group3.common.schemas import RetrievalRequest
from tests.test_references import document, reference
from tests.test_writer import writer_input
from tests.synthesis_fixtures import mock_draft, supported_review


async def test_retrieval_observe_expand_rerank_stop(tmp_path,make_paper):
    class Search:
        calls=[]
        async def search(self,topic,limit):
            self.calls.append((topic,limit))
            return [make_paper(1,year=2020)] if len(self.calls)==1 else [make_paper(i,year=2025) for i in (2,3,4)]
    class Fetch:
        calls=[]
        async def fetch(self,paper,folder):
            self.calls.append(paper.paper_id)
            return document(paper,[])
    search,fetch=Search(),Fetch()
    agent=RetrievalAgent(search,KeywordRanker(),fetch,JsonPaperStore(tmp_path),Settings(_env_file=None))
    result=await agent.run(RetrievalRequest(task_id="adaptive",topic="multi agent systems",target_papers=3,minimum_papers=3))
    assert result.status=="completed" and len(search.calls)==2
    assert [limit for _,limit in search.calls]==[9,18]
    assert make_paper(1).paper_id not in result.paper_ids
    audit=json.loads(Path(result.decisions_path).read_text(encoding="utf-8"))
    assert audit["rounds_used"]==2
    assert any(item.get("decision",{}).get("action")=="expand_search" for item in audit["decisions"])


async def test_retrieval_duplicate_pool_stops_without_redownload(tmp_path,make_paper):
    class Search:
        calls=0
        async def search(self,topic,limit):
            self.calls+=1
            return [make_paper()]
    class Fetch:
        calls=0
        async def fetch(self,paper,folder):
            self.calls+=1
            return document(paper,[])
    search,fetch=Search(),Fetch()
    result=await RetrievalAgent(search,KeywordRanker(),fetch,JsonPaperStore(tmp_path),Settings(_env_file=None,max_search_rounds=5)).run(
        RetrievalRequest(task_id="duplicate",topic="multi agent systems",target_papers=3,minimum_papers=3))
    assert result.status=="insufficient_papers" and search.calls==2 and fetch.calls==1


async def test_retrieval_budget_and_relevance_never_relaxed(tmp_path,make_paper):
    class Search:
        calls=0
        async def search(self,topic,limit):
            self.calls+=1
            return [make_paper(self.calls,title="quantum optics")]
    class Fetch:
        async def fetch(self,paper,folder):
            raise AssertionError("Unrelated papers must not be downloaded")
    search=Search()
    result=await RetrievalAgent(search,KeywordRanker(),Fetch(),JsonPaperStore(tmp_path),Settings(_env_file=None,max_search_rounds=2)).run(
        RetrievalRequest(task_id="bounded",topic="multi agent systems",target_papers=3,minimum_papers=3))
    assert result.status=="insufficient_papers" and result.selected_count==0 and search.calls==2


async def test_unavailable_primary_not_retried_on_replanning(tmp_path,make_paper):
    from group3.agents.retrieval.search import ResilientSearch
    from group3.agents.retrieval.downloader import HttpRequestError
    class Primary:
        calls=0
        async def search(self,topic,limit):
            self.calls+=1
            raise HttpRequestError("fixture capacity",code="rate_limited",attempts=1,status_code=429)
    class Secondary:
        calls=0
        warnings=[]
        async def search(self,topic,limit):
            self.calls+=1
            return [make_paper(i) for i in range(self.calls)]
    class Fetch:
        async def fetch(self,paper,folder):
            return document(paper,[])
    primary,secondary=Primary(),Secondary()
    result=await RetrievalAgent(ResilientSearch(primary,secondary),KeywordRanker(),Fetch(),JsonPaperStore(tmp_path),Settings(_env_file=None)).run(
        RetrievalRequest(task_id="circuit",topic="multi agent systems",target_papers=3,minimum_papers=3))
    assert result.status=="completed" and primary.calls==1 and secondary.calls==3


@pytest.mark.parametrize("off_topic",[False,True])
async def test_model_retrieval_decision_is_bounded(off_topic):
    def handler(request):
        value={"action":"rewrite_query","query":"quantum optics" if off_topic else "multi agent language models","reason":"Try a focused query."}
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":json.dumps(value)}}]})
    request=RetrievalRequest(task_id="plan",topic="multi agent large language models",target_papers=3,minimum_papers=3)
    obs=SearchObservation(1,request.topic,9,1,1,1,1,0,None,[])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        action=await GroqRetrievalPlanner(client,"fixture-key","openai/gpt-oss-20b").decide(request,obs,[obs])
    assert action.limit==18
    assert action.action==("expand_search" if off_topic else "rewrite_query")
    assert action.query!= "quantum optics"


async def test_model_cannot_narrow_and_query_to_fix_volume_shortage():
    def handler(request):
        value={"action":"rewrite_query","query":"multi agent large language models communication","reason":"Broaden the results"}
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":json.dumps(value)}}]})
    request=RetrievalRequest(task_id="and-guard",topic="multi agent large language models",target_papers=3,minimum_papers=3)
    obs=SearchObservation(1,request.topic,9,1,1,1,1,0,None,[])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        action=await GroqRetrievalPlanner(client,"fixture-key","openai/gpt-oss-20b").decide(request,obs,[obs])
    assert action.action=="expand_search" and action.query==request.topic
    assert "stricter AND" in action.reason


def test_unsupported_numbers_and_unsourced_inference_rejected(writer_input):
    draft=mock_draft(writer_input)
    draft.introduction[0].text="성능이 99.9% 향상되었습니다."
    with pytest.raises(ValueError,match="numeric"):
        validate_draft(draft,writer_input)
    draft=mock_draft(writer_input)
    writer_input.research_gaps=[]
    draft.research_gaps=[Statement(statement_id="unsupported-gap",text="연구 공백이 있습니다.",claim_ids=[writer_input.reader_results[0].overview[0].claim_id],kind="inference")]
    with pytest.raises(ValueError,match="new gap"):
        validate_draft(draft,writer_input)


async def test_writer_support_review_withholds_text_and_saves_audit(tmp_path,writer_input):
    draft=mock_draft(writer_input)
    draft.comparison[0].text="이 문장은 검토에서 보류됩니다."
    def handler(request):
        name=json.loads(request.content)["response_format"]["json_schema"]["name"]
        output=draft
        if name=="grounded_support_review":
            output=supported_review(draft)
            next(a for a in output.assessments if a.statement_id=="compare").verdict="unsupported"
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)
    assert "이 문장은 검토에서 보류됩니다" not in result.markdown
    assert "support_review:compare" in result.missing_coverage
    assert result.status=="coverage_incomplete" and not result.evidence_verified
    assert all(Path(p).exists() for p in (result.draft_path,result.review_path,result.decisions_path))


async def test_writer_one_structural_repair_then_review(tmp_path,writer_input):
    calls=[]
    def handler(request):
        payload=json.loads(request.content)
        name=payload["response_format"]["json_schema"]["name"]
        calls.append(name)
        draft=mock_draft(writer_input)
        if len(calls)==1:
            draft.introduction[0].claim_ids=["not-supplied"]
        output=draft if name=="grounded_literature_draft" else supported_review(draft)
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path).run(writer_input)
    assert calls==["grounded_literature_draft","grounded_literature_draft","grounded_support_review"]
    trace=json.loads(Path(result.decisions_path).read_text(encoding="utf-8"))
    assert trace["decisions"][0]["outcome"]=="rejected"


async def test_real_rewrite_contract_receives_previous_report_and_feedback(tmp_path,writer_input):
    generation_inputs=[]
    def handler(request):
        payload=json.loads(request.content)
        name=payload["response_format"]["json_schema"]["name"]
        data=json.loads(payload["messages"][-1]["content"])
        draft=mock_draft(writer_input)
        if name=="grounded_literature_draft":
            generation_inputs.append(data)
            if data["coverage_feedback"]:
                draft.introduction[0].text="요청을 반영해 근거의 범위를 다시 서술했습니다."
            output=draft
        else:
            output=supported_review(draft)
        return httpx.Response(200,json={"choices":[{"finish_reason":"stop","message":{"content":output.model_dump_json()}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        agent=WriterAgent(GroqPlanner(client,"fixture-key"),tmp_path)
        first=await agent.run(writer_input)
        revision=RevisionRequest(report_id=first.report_id,feedback=CoverageFeedback(missing_sections=["introduction"],note="Clarify the scope"))
        updated=await agent.revise(revision)
        with pytest.raises(RevisionLimitError):
            await agent.revise(revision)
    assert "근거를 종합한 초안" in generation_inputs[1]["previous_report"]
    assert agent.state.previous_report(first.report_id)==first.markdown
    assert generation_inputs[1]["coverage_feedback"]["note"]=="Clarify the scope"
    assert updated.markdown!=first.markdown and "요청을 반영해" in updated.markdown


def test_reference_agent_requests_review_instead_of_guessing(make_paper):
    from group3.agents.references.agent import CommonReferencesAgent
    papers=[document(make_paper(1),[reference(doi="10.1234/a",arxiv_id="2401.99999")]),
        document(make_paper(2),[reference(doi="10.1234/b",arxiv_id="2401.99999")])]
    result=CommonReferencesAgent().analyze(papers,"review")
    assert result.review_required and result.decisions[-1]["action"]=="request_review"
    assert result.common_references==[]
