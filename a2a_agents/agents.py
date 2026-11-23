import asyncio
import httpx
from group3.cli import retrieve
from group3.common.analysis_schemas import ReferencesRequest, RevisionRequest, WriterRequest
from group3.common.config import AnalysisSettings, Settings
from group3.common.schemas import RetrievalRequest
from group3.services import analyze_references, write_report
from a2a_agents.config import WrapperSettings
from supervisor.config import SupervisorSettings

async def retrieval(request: dict) -> dict:
    """Agent 1 Retrieval agent: finds the papers for a topic and saves them in the paper store."""
    result = await retrieve(RetrievalRequest.model_validate(request), Settings())
    return result.model_dump(mode='json')

async def references(request: dict) -> dict:
    """Agent 2 References: the references cited by at least two of the papers."""
    result = await asyncio.to_thread(analyze_references, ReferencesRequest.model_validate(request), Settings())
    return result.model_dump(mode='json')

async def writer(request: dict) -> dict:
    """Writer agent: a new report, or a revision when the request has feedback."""
    parsed = RevisionRequest.model_validate(request) if 'feedback' in request else WriterRequest.model_validate(request)
    result = await write_report(parsed, AnalysisSettings())
    return result.model_dump(mode='json')

async def _forward(url: str, request: dict) -> dict:
    """Send the request to one of REST routes and return its JSON answer."""
    timeout = SupervisorSettings().agent_timeout_seconds
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as http:
        response = await http.post(url, json=request)
    if response.status_code >= 400:
        raise RuntimeError(f'{url} answered {response.status_code}: {response.text[:300]}')
    return response.json()

async def reader(request: dict) -> dict:
    """MPaper reader: reads a paper, or checks one claim when the request has evidence."""
    if 'evidence' in request:
        return await _forward(WrapperSettings().group2_reader_url + '/api/v1/verify', request)
    # Evidence must come from the paper's sections (team contract), so Gemini is not given the abstract to quote.
    return await _forward(WrapperSettings().group2_reader_url + '/api/v1/group3/read', {**request, 'abstract': None})

async def connections(request: dict) -> dict:
    """Agent 3 Connections: the connections and research gaps between the papers."""
    return await _forward(WrapperSettings().group2_connections_url + '/api/v1/group3/connections', request)