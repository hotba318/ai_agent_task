from datetime import datetime, timezone

import httpx
import pytest

from group3.agents.retrieval.agent import RetrievalAgent
from group3.agents.retrieval.arxiv_client import ArxivClient
from group3.agents.retrieval.downloader import HttpRequestError, HttpTransport, RequestGate, retry_after_seconds
from group3.agents.retrieval.ranker import KeywordRanker
from group3.agents.retrieval.storage import JsonPaperStore
from group3.common.config import Settings
from group3.common.schemas import RetrievalRequest


@pytest.mark.parametrize("header",[None,"invalid","-1"])
async def test_429_without_usable_cooldown_does_not_retry(header):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(429,headers={"Retry-After":header} if header else {})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HttpRequestError) as exc:
            await HttpTransport(client,RequestGate(0),retries=2).request("GET","https://export.arxiv.org/api/query")
    assert len(calls)==1 and exc.value.status_code==429
    assert exc.value.code=="rate_limited" and "retry later" in str(exc.value)


async def test_429_respects_provided_cooldown():
    starts,now=[],[0.0]
    async def sleep(delay):
        now[0]+=delay
    def handler(request):
        starts.append(now[0])
        return httpx.Response(429 if len(starts)==1 else 200,headers={"Retry-After":"10"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response=await HttpTransport(client,RequestGate(3,clock=lambda:now[0],sleep=sleep),sleep=sleep).request("GET","https://export.arxiv.org/api/query")
    assert response.status_code==200 and starts==[0,10]


def test_http_date_retry_after():
    now=datetime(2026,11,5,1,0,tzinfo=timezone.utc)
    assert retry_after_seconds("Thu, 05 Nov 2026 01:00:45 GMT",now)==45
    assert retry_after_seconds("Thu, 05 Nov 2026 00:59:00 GMT",now)==0
    assert retry_after_seconds("broken",now) is None


@pytest.mark.parametrize("status",[429,503])
async def test_long_cooldown_is_returned_without_blocking(status):
    async def sleep(delay):
        raise AssertionError("must not block on a long server cooldown")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(status,headers={"Retry-After":"3600"}))) as client:
        with pytest.raises(HttpRequestError) as exc:
            await HttpTransport(client,RequestGate(0),sleep=sleep).request("GET","https://export.arxiv.org/api/query")
    assert exc.value.retry_after==3600 and exc.value.attempts==1


async def test_error_preserves_status_and_omits_credentials():
    async def sleep(delay):
        pass
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(503))) as client:
        with pytest.raises(HttpRequestError) as exc:
            await HttpTransport(client,RequestGate(0),retries=1,sleep=sleep).request("GET","https://user:password@example.test/api?token=secret")
    message=str(exc.value)
    assert "HTTP 503" in message and exc.value.attempts==2
    assert not any(value in message for value in ("password","secret","user:"))
    assert isinstance(exc.value.__cause__,httpx.HTTPStatusError)


async def test_agent_preserves_rate_limit_failure(tmp_path):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(429))) as client:
        search=ArxivClient(HttpTransport(client,RequestGate(0)))
        agent=RetrievalAgent(search,KeywordRanker(),None,JsonPaperStore(tmp_path),Settings())
        result=await agent.run(RetrievalRequest(task_id="limited",topic="multi agent",target_papers=3,minimum_papers=3))
    assert result.status=="failed" and result.selected_count==0
    assert result.failures[0].code=="arxiv_rate_limited"
    assert "HTTP 429" in result.failures[0].detail
    assert "search failed before document collection" in result.warnings[0]
