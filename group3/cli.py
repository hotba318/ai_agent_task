import argparse
import asyncio
from pathlib import Path

import httpx

from group3.common.config import Settings
from group3.common.schemas import RetrievalRequest
from group3.agents.retrieval.agent import RetrievalAgent
from group3.agents.retrieval.arxiv_client import ArxivClient
from group3.agents.retrieval.downloader import HttpTransport, RequestGate
from group3.agents.retrieval.fetcher import DocumentPipeline
from group3.agents.retrieval.ranker import KeywordRanker
from group3.agents.retrieval.storage import JsonPaperStore
from group3.agents.retrieval.datacite_client import DataCiteClient
from group3.agents.retrieval.search import ResilientSearch
from group3.agents.retrieval.planner import GroqRetrievalPlanner
from group3.common.config import AnalysisSettings


async def retrieve(request, settings):
    async with httpx.AsyncClient(timeout=settings.timeout_seconds, follow_redirects=True,
                                 headers={"User-Agent": settings.user_agent},
                                 limits=httpx.Limits(max_connections=1)) as client:
        api = HttpTransport(client, RequestGate(settings.api_delay_seconds), settings.retries)
        # auto should move to the independent service after one availability failure,
        # rather than repeatedly hit a capacity-limited arXiv backend.
        primary = ArxivClient(HttpTransport(client, api.gate, retries=0)) if settings.search_provider == "auto" else ArxivClient(api)
        datacite = DataCiteClient(api)
        search = ResilientSearch(primary, datacite) if settings.search_provider == "auto" else datacite if settings.search_provider == "datacite" else primary
        downloads = HttpTransport(client, RequestGate(settings.download_delay_seconds), settings.retries)
        grobid = HttpTransport(client, RequestGate(0), settings.retries)
        planner=None
        analysis=AnalysisSettings()
        key=analysis.groq_api_key.get_secret_value() if analysis.groq_api_key else ""
        if settings.retrieval_planner_mode=="groq" and not key:
            raise ValueError("GROQ_API_KEY is required for the Groq retrieval planner")
        if settings.retrieval_planner_mode!="rules" and key:
            planner=GroqRetrievalPlanner(client,key,analysis.groq_model,max_rounds=settings.max_search_rounds,candidate_multiplier=settings.candidate_multiplier)
        agent = RetrievalAgent(search, KeywordRanker(settings.freshness_field),
            DocumentPipeline(downloads, grobid, settings.grobid_url, settings.preferred_format), JsonPaperStore(settings.store_root), settings,planner)
        return await agent.run(request)


def main():
    parser = argparse.ArgumentParser(description="Agent 1: live arXiv retrieval")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--task-id", default="retrieval")
    parser.add_argument("--target", type=int)
    parser.add_argument("--minimum", type=int)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--search-provider", choices=["auto", "arxiv", "datacite"])
    args = parser.parse_args()
    settings = Settings()
    if args.search_provider:
        settings.search_provider = args.search_provider
    request = RetrievalRequest(task_id=args.task_id, topic=args.topic,
        target_papers=args.target if args.target is not None else settings.target_papers,
        minimum_papers=args.minimum if args.minimum is not None else settings.minimum_papers)
    result = asyncio.run(retrieve(request, settings))
    output = result.model_dump_json(indent=2)
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(output, encoding="utf-8")
    print(output)
    return 0 if result.status == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
