from pathlib import Path
from uuid import uuid4

from aiohttp import request
from group3.common.analysis_schemas import (
    Claim,
    Connection,
    ReaderResult,
    ReferencesRequest,
    RevisionRequest,
    WriterRequest,
    WriterResult,
)
from group3.agents.references.agent import CommonReferencesAgent
from group3.agents.retrieval.storage import JsonPaperStore
from group3.agents.writer.validator import validate_input
from group3.common.schemas import RetrievalRequest, RetrievalResult
from supervisor.fakes.sample import sample_input, sample_report

FAKE_STORE = JsonPaperStore(Path(__file__).resolve().parents[2] / 'data' / 'fake-papers')

def answer_retrieval(request: dict) -> dict:
    """Fake Agent 1: finds the 8 sample papers and saves them in a paper store, like the real agent."""
    req = RetrievalRequest.model_validate(request)
    run_id = f'fake-{uuid4().hex[:8]}'
    folder = FAKE_STORE.begin(req.task_id, run_id)
    papers = sample_input().papers
    for paper in papers:
        FAKE_STORE.save(folder, paper)
    result = RetrievalResult(
        task_id=req.task_id,
        run_id=run_id,
        status='completed',
        requested_count=req.target_papers,
        selected_count=len(papers),
        paper_store_uri=folder.as_uri(),
        paper_ids=[paper.paper_id for paper in papers],
    )
    FAKE_STORE.finish(folder, result)
    return result.model_dump(mode='json')


def answer_references(request: dict) -> dict:
    """Fake Agent 2: Junkyung's real reference matching, run on the fake paper store."""
    req = ReferencesRequest.model_validate(request)
    folder = FAKE_STORE.root / req.task_id / req.run_id
    return CommonReferencesAgent().run(req, FAKE_STORE, folder).model_dump(mode='json')


def _all_claims(reader_result: ReaderResult) -> list[Claim]:
    """Every claim of one paper, in the contract's field order."""
    return (reader_result.overview + reader_result.methods + reader_result.datasets
            + reader_result.results + reader_result.limitations)


def answer_reader(request: dict) -> dict:
    """Fake paper reader: reads one paper, or answers a verify request with the quote itself as the corrected claim."""
    if 'evidence' in request:
        return {'verified': False, 'corrected_claim': request['evidence']['quote'], 'notes': 'fake: the quote itself'}
    paper_id = request['paper_id']
    sample = sample_input()
    reader_result = next((r for r in sample.reader_results if r.paper_id == paper_id), None)
    if reader_result is None:
        raise ValueError(f'unknown paper: {paper_id}')
    cited = {evidence_id for claim in _all_claims(reader_result) for evidence_id in claim.evidence_ids}
    evidence = [e for e in sample.evidence if e.evidence_id in cited]
    return {
        'reader_result': reader_result.model_dump(mode='json'),
        'evidence': [e.model_dump(mode='json') for e in evidence],
    }


def answer_connections(request: dict) -> dict:
    """Fake Agent 3: a made-up 'conflict' copying the first claims of the first two papers, IDs included, as Gemini might."""    
    reader_results = [ReaderResult.model_validate(item) for item in request['reader_results']]
    first_claims = [_all_claims(result)[0] for result in reader_results[:2]]
    connection = Connection(connection_id='fake-conflict-1', kind='conflict', claims=first_claims)
    return {'connections': [connection.model_dump(mode='json')], 'research_gaps': []}


_task_by_report: dict[str, str] = {}


def answer_writer(request: dict) -> dict:
    """Fake Agent 4: the sample report; a RevisionRequest gets revision 1 of the same report."""
    if 'feedback' in request:
        revision_request = RevisionRequest.model_validate(request)
        report_id = revision_request.report_id
        task_id = _task_by_report.get(report_id, 'unknown')
        revision = 1
    else:
        writer_request = WriterRequest.model_validate(request)
        validate_input(writer_request)
        report_id = uuid4().hex
        task_id = writer_request.task_id
        revision = 0
        _task_by_report[report_id] = task_id
    result = WriterResult(
        task_id=task_id,
        report_id=report_id,
        revision=revision,
        status='needs_review',
        markdown_path='fake://report.md',
        evidence_path='fake://evidence.json',
        markdown=sample_report(),
        missing_coverage=[],
        warnings=[],
        mode='extractive',
    )
    return result.model_dump(mode='json')
