import json
from dataclasses import asdict
from uuid import uuid4

from group3.common.config import Settings
from group3.common.interfaces import DocumentFetcher, PaperStore, Ranker, SearchProvider
from group3.common.schemas import Failure, RetrievalRequest, RetrievalResult
from .downloader import HttpRequestError
from .fetcher import FetchError
from .planner import RuleRetrievalPlanner, SearchObservation


class RetrievalAgent:
    def __init__(self, search: SearchProvider, ranker: Ranker, fetcher: DocumentFetcher,
                 store: PaperStore, settings: Settings, planner=None):
        self.search, self.ranker, self.fetcher = search, ranker, fetcher
        self.store, self.settings = store, settings
        self.planner = planner or RuleRetrievalPlanner(settings.max_search_rounds, settings.candidate_multiplier)

    async def run(self, request: RetrievalRequest) -> RetrievalResult:
        run_id = uuid4().hex
        folder = self.store.begin(request.task_id, run_id)
        pool, documents, attempted = {}, {}, set()
        ids, failures, warnings, history, trace = [], [], [], [], []
        observation = None
        any_search_succeeded = False
        for _ in range(self.settings.max_search_rounds + 1):
            try:
                action = await self.planner.decide(request, observation, history)
            except Exception as exc:
                warnings.append(f"Retrieval planner unavailable ({type(exc).__name__}); used bounded rule policy.")
                action = await RuleRetrievalPlanner(self.settings.max_search_rounds, self.settings.candidate_multiplier).decide(request, observation, history)
            trace.append({"planner": self.planner.mode, "decision": asdict(action)})
            if action.action == "stop":
                break
            round_no = len(history) + 1
            if round_no > self.settings.max_search_rounds or action.limit > request.target_papers * self.settings.candidate_multiplier * self.settings.max_search_rounds:
                raise ValueError("retrieval planner exceeded search budget")
            before = set(pool)
            parse_failures, error, candidates = 0, None, []
            try:
                candidates = await self.search.search(action.query, action.limit)
                for paper in candidates:
                    if paper.paper_id not in pool or paper.updated_date > pool[paper.paper_id].updated_date:
                        if paper.paper_id in documents and documents[paper.paper_id].version_id!=paper.version_id:
                            documents.pop(paper.paper_id)
                            attempted.discard(paper.paper_id)
                        pool[paper.paper_id] = paper
                ranked = self.ranker.rank(request.topic, list(pool.values()))
                any_search_succeeded = True
            except Exception as exc:
                ranked = []
                source = getattr(self.search, "error_source", "arxiv")
                error = source + "_" + exc.code if isinstance(exc, HttpRequestError) else type(exc).__name__
                failures.append(Failure(stage="search_rank", code=error, detail=str(exc)))
            warnings.extend(getattr(self.search, "warnings", []))
            if not error:
                current = []
                for paper in ranked:
                    if paper.paper_id not in documents and paper.paper_id not in attempted:
                        attempted.add(paper.paper_id)
                        try:
                            document = await self.fetcher.fetch(paper, folder)
                            self.store.save(folder, document)
                            documents[paper.paper_id] = document
                            warnings.extend(f"{paper.paper_id}: {w}" for w in document.warnings)
                        except FetchError as exc:
                            failures.extend(exc.failures)
                            parse_failures += 1
                        except Exception as exc:
                            failures.append(Failure(paper_id=paper.paper_id, stage="fetch_store", code=type(exc).__name__, detail=str(exc)))
                            parse_failures += 1
                    if paper.paper_id in documents:
                        current.append(paper.paper_id)
                    if len(current) == request.target_papers:
                        break
                ids = current
            observation = SearchObservation(round_no, action.query, action.limit, len(candidates), len(ranked), len(set(pool)-before),
                len(ids), parse_failures, error, [{"paper_id": p.paper_id, "title": p.title, "abstract": (p.abstract or "")[:350]} for p in candidates[:5]])
            history.append(observation)
            trace.append({"observation": asdict(observation)})
        if len(ids) < request.target_papers:
            reason = "search failed before document collection" if not any_search_succeeded else "bounded search stopped with too few eligible papers"
            warnings.append(f"Requested {request.target_papers}; collected {len(ids)}; {reason}. Minimum {request.minimum_papers}.")
        path = folder / "decisions.json"
        path.write_text(json.dumps({"topic": request.topic, "max_rounds": self.settings.max_search_rounds,
            "rounds_used": len(history), "decisions": trace}, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "completed" if len(ids) >= request.minimum_papers else "insufficient_papers" if any_search_succeeded else "failed"
        result = RetrievalResult(task_id=request.task_id, run_id=run_id, status=status, requested_count=request.target_papers,
            selected_count=len(ids), paper_store_uri=folder.as_uri(), paper_ids=ids, warnings=list(dict.fromkeys(warnings)), failures=failures, decisions_path=str(path))
        self.store.finish(folder, result)
        return result
