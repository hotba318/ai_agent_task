"""Application wiring shared by standalone CLI and version-specific A2A adapter."""
import httpx

from group3.common.analysis_schemas import ReferencesRequest, RevisionRequest, WriterRequest
from group3.common.config import AnalysisSettings, Settings
from group3.agents.references.agent import CommonReferencesAgent
from group3.agents.retrieval.storage import JsonPaperStore
from group3.agents.writer.agent import WriterAgent
from group3.agents.writer.planner import ExtractivePlanner, GroqPlanner


def analyze_references(request: ReferencesRequest, settings: Settings):
    # Validated path segments; services never accept arbitrary client file paths.
    store = JsonPaperStore(settings.store_root)
    folder = store.root / request.task_id / request.run_id
    if not folder.resolve().is_relative_to(store.root):
        raise ValueError("Paper Store selection escapes configured root")
    return CommonReferencesAgent().run(request, store, folder)


async def write_report(request: WriterRequest | RevisionRequest, settings: AnalysisSettings):
    async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
        planner = ExtractivePlanner() if settings.writer_mode == "extractive" else GroqPlanner(
            client, settings.groq_api_key.get_secret_value() if settings.groq_api_key else "", settings.groq_model)
        agent = WriterAgent(planner, settings.output_root)
        return await agent.revise(request) if isinstance(request, RevisionRequest) else await agent.run(request)
