"""Offline synthetic DOI API fixtures only; these are not live paper observations."""
import copy
import json
from datetime import date

import httpx
import pytest

from group3.agents.retrieval.agent import RetrievalAgent
from group3.agents.retrieval.datacite_client import DataCiteClient, parse_arxiv_record
from group3.agents.retrieval.downloader import HttpRequestError, HttpTransport, RequestGate
from group3.agents.retrieval.ranker import KeywordRanker
from group3.agents.retrieval.search import ResilientSearch
from group3.agents.retrieval.storage import JsonPaperStore
from group3.common.config import Settings
from group3.common.schemas import RetrievalRequest


@pytest.fixture
def record():
    return {"attributes":{"doi":"10.48550/arxiv.2401.00001","publisher":"arXiv",
        "url":"https://arxiv.org/abs/2401.00001","version":"3",
        "titles":[{"title":"Synthetic multi agent language models"}],
        "creators":[{"name":"Fixture Author"}],"created":"2026-11-05T00:00:00Z",
        "descriptions":[{"descriptionType":"Abstract","description":"Synthetic multi agent language models abstract"}],
        "dates":[{"dateType":"Submitted","dateInformation":"v1","date":"2024-01-01T01:00:00Z"},
                 {"dateType":"Submitted","dateInformation":"v3","date":"2024-02-01T01:00:00Z"},
                 {"dateType":"Updated","dateInformation":"v3","date":"2026-11-01T01:00:00Z"}]}}


def test_verified_datacite_metadata(record):
    paper=parse_arxiv_record(record)
    assert paper.metadata_source=="datacite"
    assert str(paper.metadata_url).startswith("https://api.datacite.org/dois/10.48550/arxiv.")
    assert paper.submitted_date==date(2024,1,1) and paper.updated_date==date(2024,2,1)
    assert paper.version_id=="2401.00001v3"
    assert str(paper.html_url)=="https://arxiv.org/html/2401.00001v3"


@pytest.mark.parametrize("corruption",["doi","url_id","host","publisher","missing_v1","missing_current_date","invalid_date","chronology"])
def test_no_guessed_identity_or_dates(record,corruption):
    a=record["attributes"]
    if corruption=="doi":
        a["doi"]="10.1234/nonarxiv"
    elif corruption=="url_id":
        a["url"]="https://arxiv.org/abs/2401.99999"
    elif corruption=="host":
        a["url"]="https://other.invalid/abs/2401.00001"
    elif corruption=="publisher":
        a["publisher"]="Other repository"
    elif corruption=="missing_v1":
        a["dates"]=a["dates"][1:]
    elif corruption=="missing_current_date":
        a["version"]="4"
    elif corruption=="invalid_date":
        a["dates"][0]["date"]="2024"
    else:
        a["dates"][0]["date"]="2025-01-01"
    with pytest.raises(ValueError):
        parse_arxiv_record(record)


async def test_live_query_contract_and_invalid_records(record):
    bad=copy.deepcopy(record)
    bad["attributes"]["dates"]=[]
    def handler(request):
        assert request.url.host=="api.datacite.org"
        assert request.url.params["prefix"]=="10.48550"
        assert request.url.params["sort"]=="relevance"
        assert request.url.params["page[size]"]=="9"
        assert request.url.params["query"]=='"multi" AND "agent"'
        return httpx.Response(200,json={"data":[record,bad]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        search=DataCiteClient(HttpTransport(client,RequestGate(0)))
        papers=await search.search("multi agent",9)
    assert len(papers)==1 and len(search.warnings)==1


class Stub:
    def __init__(self,papers=None,error=None):
        self.papers,self.error,self.calls=papers or [],error,0
        self.warnings=[]
    async def search(self,topic,limit):
        self.calls+=1
        if self.error:
            raise self.error
        return self.papers


async def test_primary_success_uses_only_arxiv(make_paper):
    primary,secondary=Stub([make_paper()]),Stub()
    search=ResilientSearch(primary,secondary)
    assert await search.search("multi agent",9)
    assert secondary.calls==0 and not search.warnings


@pytest.mark.parametrize("code,status",[("rate_limited",429),("http_error",503),("network_error",None),("timeout",None)])
async def test_availability_failure_switches_services(make_paper,code,status):
    primary=Stub(error=HttpRequestError("fixture",code=code,attempts=1,status_code=status))
    secondary=Stub([make_paper()])
    search=ResilientSearch(primary,secondary)
    assert await search.search("multi agent",9)
    assert primary.calls==1 and secondary.calls==1
    assert "not arXiv API recovery" in search.warnings[0]


async def test_query_or_parser_bug_does_not_silently_fallback():
    secondary=Stub()
    search=ResilientSearch(Stub(error=ValueError("fixture malformed response")),secondary)
    with pytest.raises(ValueError):
        await search.search("multi agent",9)
    assert secondary.calls==0


async def test_secondary_failure_is_not_mislabeled_arxiv(tmp_path):
    primary=Stub(error=HttpRequestError("primary fixture",code="rate_limited",attempts=1,status_code=429))
    secondary=Stub(error=HttpRequestError("secondary fixture",code="rate_limited",attempts=1,status_code=429))
    search=ResilientSearch(primary,secondary)
    agent=RetrievalAgent(search,KeywordRanker(),None,JsonPaperStore(tmp_path),Settings())
    result=await agent.run(RetrievalRequest(task_id="both_failed",topic="multi agent",target_papers=3,minimum_papers=3))
    assert result.status=="failed" and result.selected_count==0
    assert result.failures[0].code=="datacite_rate_limited"
    assert result.warnings


def test_provider_configuration(monkeypatch):
    monkeypatch.setenv("GROUP3_SEARCH_PROVIDER","datacite")
    assert Settings(_env_file=None).search_provider=="datacite"
