import httpx
import asyncio
from pathlib import Path
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from uuid import uuid4
from group3.common.llm import TokenBudget
from group3.common.analysis_schemas import (Claim, Connection, Evidence, 
                                            ReaderResult, ReferencesRequest, ReferencesResult,
                                            RevisionRequest, WriterRequest, WriterResult)
from group3.common.schemas import PaperDocument, RetrievalRequest, RetrievalResult
from supervisor.client import call_agent
from supervisor.config import SupervisorSettings
from supervisor.memory import RunMemory
from supervisor.papers import load_papers
from supervisor.evidence import EvidenceStore
from supervisor.report import save_report, supervisor_section
from supervisor.validation import CLAIM_FIELDS, UnverifiedClaim, ClaimProblem, check_connections, all_claims, check_paper, coverage_feedback

MIN_PAPERS_TO_COMPARE = 2
CLOSEST_PASSAGES = 3
Progress = Callable[[str], Awaitable[None]]
Decide = Callable[[list[UnverifiedClaim]], Awaitable[set[str]]]

class RunStopped(Exception):
    """The run cannot continue; the message says why, for the user."""
async def retrieve(
    topic: str, task_id: str, settings: SupervisorSettings, memory: RunMemory,
) -> tuple[RetrievalResult, list[PaperDocument], list[str]]:
    """Step 1: ask the retrieval agent for papers, then load them from its paper store."""
    await memory.record_step(task_id, 'retrieval', 'working')
    request = RetrievalRequest(
        task_id=task_id,
        topic=topic,
        target_papers=settings.target_papers,
        minimum_papers=settings.minimum_papers,
    )
    try:
        reply = await call_agent(settings.retrieval_url, request.model_dump(mode='json'), settings.agent_timeout_seconds)
        retrieval = RetrievalResult.model_validate(reply)
    except Exception as error:
        await memory.record_step(task_id, 'retrieval', 'failed', notes=_short(error))
        raise RunStopped(f'The retrieval agent failed ({_short(error)}).') from error
    if retrieval.status == 'failed':
        await memory.record_step(task_id, 'retrieval', 'failed', notes=str(retrieval.failures)[:150])
        raise RunStopped(f'Retrieval failed: {retrieval.failures}')
    if retrieval.selected_count < MIN_PAPERS_TO_COMPARE:
        await memory.record_step(task_id, 'retrieval', 'failed', notes=f'{retrieval.selected_count} paper(s)')
        raise RunStopped(f'Only {retrieval.selected_count} paper(s) found; at least {MIN_PAPERS_TO_COMPARE} are needed to compare papers.')
    warnings = list(retrieval.warnings)
    if retrieval.status == 'insufficient_papers':
        warnings.append(f'Only {retrieval.selected_count} of {retrieval.requested_count} requested papers were found.')
    await memory.record_step(task_id, 'retrieval', 'completed', notes=f'{retrieval.selected_count} papers')
    return retrieval, load_papers(retrieval), warnings


def _short(error: Exception) -> str:
    """An error as one short line for a warning: its type and the start of its message."""
    return f'{type(error).__name__}: {str(error)[:150]}'

def prefix_ids(paper_id: str, reader_result: ReaderResult, evidence: list[Evidence]) -> tuple[ReaderResult, list[Evidence]]:
    """Put the paper ID in front of every claim and evidence ID, so IDs from different readers never clash."""
    
    def renamed(claim: Claim) -> Claim:
        return claim.model_copy(update={
            'claim_id': f'{paper_id}#{claim.claim_id}',
            'evidence_ids': [f'{paper_id}#{evidence_id}' for evidence_id in claim.evidence_ids],
        })
    reader_result = reader_result.model_copy(
        update={field: [renamed(claim) for claim in getattr(reader_result, field)] for field in CLAIM_FIELDS},
    )
    evidence = [item.model_copy(update={'evidence_id': f'{paper_id}#{item.evidence_id}'}) for item in evidence]
    return reader_result, evidence


async def read_paper(paper: PaperDocument, settings: SupervisorSettings) -> tuple[ReaderResult, list[Evidence]]:
    """One paper reader call: the reader result for one paper and the evidence its claims cite."""
    reply = await call_agent(settings.reader_url, paper.model_dump(mode='json'), settings.agent_timeout_seconds)
    reader_result = ReaderResult.model_validate(reply['reader_result'])
    evidence = [Evidence.model_validate(item) for item in reply['evidence']]
    return prefix_ids(paper.paper_id, reader_result, evidence)


async def read_all_papers(
    task_id: str, papers: list[PaperDocument], settings: SupervisorSettings, memory: RunMemory,
) -> tuple[list[PaperDocument], list[ReaderResult], list[Evidence], list[str]]:
    """Step 2: one reader per paper, all at the same time; a failed read is retried once, then the paper is dropped."""
    for paper in papers:
        await memory.record_step(task_id, 'reader', 'working', item=paper.paper_id)
    readings = await asyncio.gather(*(read_paper(paper, settings) for paper in papers), return_exceptions=True)
    failed = [index for index, reading in enumerate(readings) if isinstance(reading, Exception)]
    for index in failed:
        await memory.record_step(task_id, 'reader', 'working', item=papers[index].paper_id,
                                 notes=f'retrying after {_short(readings[index])}', retry=True)
    retried = await asyncio.gather(*(read_paper(papers[index], settings) for index in failed), return_exceptions=True)
    for index, reading in zip(failed, retried):
        readings[index] = reading

    warnings = []
    read_papers, reader_results, evidence = [], [], []
    for paper, reading in zip(papers, readings):
        if isinstance(reading, Exception):
            await memory.record_step(task_id, 'reader', 'failed', item=paper.paper_id, notes=_short(reading))
            warnings.append(f'Paper {paper.paper_id} was dropped: its reader failed twice ({_short(reading)}).')
            continue
        await memory.record_step(task_id, 'reader', 'completed', item=paper.paper_id, notes=f'{len(reading[1])} evidence')
        read_papers.append(paper)
        reader_results.append(reading[0])
        evidence.extend(reading[1])
    if len(read_papers) < MIN_PAPERS_TO_COMPARE:
        raise RunStopped(f'Only {len(read_papers)} paper(s) could be read; at least {MIN_PAPERS_TO_COMPARE} are needed.')
    return read_papers, reader_results, evidence, warnings


async def check_evidence(
    task_id: str, papers: list[PaperDocument], reader_results: list[ReaderResult], evidence: list[Evidence],
    settings: SupervisorSettings, memory: RunMemory,
) -> tuple[list[PaperDocument], list[ReaderResult], list[Evidence], list[UnverifiedClaim], int, list[str]]:
    """Step 3: check every paper's claims against their quotes; drop papers left with no claims."""
    budget = TokenBudget()
    warnings, problems, unjudged, judge_error, corrected = [], [], [], None, 0
    kept_papers, kept_results, kept_evidence = [], [], []
    async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as http:
        for paper, reader_result in zip(papers, reader_results):
            await memory.record_step(task_id, 'evidence', 'working', item=paper.paper_id)
            own = [item for item in evidence if item.evidence_id.startswith(f'{paper.paper_id}#')]
            checked = await check_paper(http, paper, reader_result, own, settings, budget)
            problems.extend(checked.unverified)
            corrected += checked.corrected
            if checked.judge_error is not None:
                unjudged.append(paper.paper_id)
                judge_error = checked.judge_error
            kept = len(all_claims(checked.reader_result))
            notes = f'{kept} kept, {checked.corrected} corrected, {len(checked.unverified)} unable to verify'
            if kept == 0:
                await memory.record_step(task_id, 'evidence', 'failed', item=paper.paper_id, notes=notes)
                warnings.append(f'Paper {paper.paper_id} was dropped: none of its claims could be verified.')
                continue
            await memory.record_step(task_id, 'evidence', 'completed', item=paper.paper_id, notes=notes)
            kept_papers.append(paper)
            kept_results.append(checked.reader_result)
            kept_evidence.extend(checked.evidence)
    if unjudged:
        warnings.append(f'The judge could not check the claims of {len(unjudged)} paper(s) ({_short(judge_error)}): {", ".join(unjudged)}.')
    if len(kept_papers) < MIN_PAPERS_TO_COMPARE:
        raise RunStopped(f'Only {len(kept_papers)} paper(s) have verified claims; at least {MIN_PAPERS_TO_COMPARE} are needed.')
    unverified, store_warnings = await find_closest_passages(task_id, papers, problems)
    return kept_papers, kept_results, kept_evidence, unverified, corrected, warnings + store_warnings


async def find_closest_passages(
    task_id: str, papers: list[PaperDocument], problems: list[ClaimProblem],
) -> tuple[list[UnverifiedClaim], list[str]]:
    """For each claim that could not be verified, its paper's closest passages; the store is built only when needed."""
    if not problems:
        return [], []
    problem_papers = {problem.paper_id for problem in problems}
    store = None
    try:
        store = EvidenceStore(task_id)
        await store.add_papers([paper for paper in papers if paper.paper_id in problem_papers])
        unverified = []
        for problem in problems:
            closest = await store.search(problem.claim.text, problem.paper_id, CLOSEST_PASSAGES)
            unverified.append(UnverifiedClaim(problem.paper_id, problem.claim, problem.reason, closest, problem.keepable))
        return unverified, []
    except Exception as error:
        unverified = [UnverifiedClaim(problem.paper_id, problem.claim, problem.reason, [], problem.keepable) for problem in problems]
        return unverified, [f'Closest passages are missing: the evidence store failed ({_short(error)}).']
    finally:
        if store is not None:
            store.delete()


async def find_references(
    task_id: str, run_id: str, papers: list[PaperDocument], settings: SupervisorSettings, memory: RunMemory,
) -> ReferencesResult:
    """Step 4: Agent 2 finds the references the final papers share; tried twice, then the run stops."""
    await memory.record_step(task_id, 'references', 'working')
    request = ReferencesRequest(
        task_id=task_id,
        run_id=run_id,
        paper_ids=[paper.paper_id for paper in papers],
        min_citing_papers=settings.min_citing_papers,
    )
    for attempt in (1, 2):
        try:
            reply = await call_agent(settings.references_url, request.model_dump(mode='json'), settings.agent_timeout_seconds)
            references = ReferencesResult.model_validate(reply)
        except Exception as error:
            if attempt == 2:
                await memory.record_step(task_id, 'references', 'failed', notes=_short(error))
                raise RunStopped(f'Agent 2 failed twice, and the writer needs the common references ({_short(error)}).') from error
            await memory.record_step(task_id, 'references', 'working', notes=f'retrying after {_short(error)}', retry=True)
            continue
        await memory.record_step(task_id, 'references', 'completed', notes=f'{len(references.common_references)} common references')
        return references
    

async def find_connections(
    task_id: str, reader_results: list[ReaderResult], evidence: list[Evidence],
    settings: SupervisorSettings, memory: RunMemory,
) -> tuple[list[Connection], list[Claim], list[str]]:
    """Step 5: Agent 3 compares the papers and its answer is checked; a failure becomes a warning and an empty result."""
    await memory.record_step(task_id, 'connections', 'working')
    request = {
        'reader_results': [result.model_dump(mode='json') for result in reader_results],
        'evidence': [item.model_dump(mode='json') for item in evidence],
    }
    try:
        reply = await call_agent(settings.connections_url, request, settings.agent_timeout_seconds)
        connections = [Connection.model_validate(item) for item in reply['connections']]
        research_gaps = [Claim.model_validate(item) for item in reply['research_gaps']]
    except Exception as error:
        await memory.record_step(task_id, 'connections', 'failed', notes=_short(error))
        return [], [], [f'Connections and research gaps are missing: Agent 3 failed ({_short(error)}).']
    reader_claim_ids = {claim.claim_id for result in reader_results for claim in all_claims(result)}
    async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as http:
        connections, research_gaps, warnings = await check_connections(
            http, connections, research_gaps, evidence, reader_claim_ids, settings, TokenBudget())
    await memory.record_step(task_id, 'connections', 'completed', notes=f'{len(connections)} connection(s), {len(research_gaps)} gap(s) after checks')
    return connections, research_gaps, warnings

async def write_draft(
    task_id: str,
    topic: str,
    papers: list[PaperDocument],
    reader_results: list[ReaderResult],
    evidence: list[Evidence],
    references: ReferencesResult,
    connections: list[Connection],
    research_gaps: list[Claim],
    settings: SupervisorSettings,
    memory: RunMemory,
) -> WriterResult:
    """Step 6: the writer turns everything into a draft report; if it fails, the run stops."""
    await memory.record_step(task_id, 'writer', 'working')
    request = WriterRequest(
        task_id=task_id,
        topic=topic,
        papers=papers,
        reader_results=reader_results,
        evidence=evidence,
        common_references=references,
        connections=connections,
        research_gaps=research_gaps,
    )
    try:
        reply = await call_agent(settings.writer_url, request.model_dump(mode='json'), settings.agent_timeout_seconds)
        draft = WriterResult.model_validate(reply)
    except Exception as error:
        await memory.record_step(task_id, 'writer', 'failed', notes=_short(error))
        raise RunStopped(f'The writer failed, so there is no report ({_short(error)}).') from error
    await memory.record_step(task_id, 'writer', 'completed', notes=f'report {draft.report_id}, revision {draft.revision}')
    return draft

async def review_coverage(
    task_id: str, draft: WriterResult, settings: SupervisorSettings, memory: RunMemory,
) -> tuple[WriterResult, list[str]]:
    """Step 7: send the draft back once if it left out what its input supports; remaining gaps become warnings."""
    feedback = coverage_feedback(draft.missing_coverage)
    warnings, status = [], 'completed'
    if feedback is not None and settings.coverage_retries > 0:
        await memory.record_step(task_id, 'coverage', 'working', notes=f'revision for {", ".join(feedback.missing_sections)}')
        request = RevisionRequest(report_id=draft.report_id, feedback=feedback)
        try:
            reply = await call_agent(settings.writer_url, request.model_dump(mode='json'), settings.agent_timeout_seconds)
            draft = WriterResult.model_validate(reply)
        except Exception as error:
            status = 'failed'
            warnings.append(f'The coverage revision failed, so the first draft is kept ({_short(error)}).')
    if draft.missing_coverage:
        warnings.append(f'Coverage gaps the writer could not fill: {", ".join(draft.missing_coverage)}.')
    await memory.record_step(task_id, 'coverage', status, notes=f'revision {draft.revision}, {len(draft.missing_coverage)} gap(s) left')
    return draft, warnings


@dataclass
class RunOutput:
    """Everything one run produced: the draft, plus what the supervisor needs to validate it."""
    task_id: str
    topic: str
    papers: list[PaperDocument]
    reader_results: list[ReaderResult]
    evidence: list[Evidence]
    references: ReferencesResult
    connections: list[Connection]
    research_gaps: list[Claim]
    unverified: list[UnverifiedClaim]
    draft: WriterResult
    warnings: list[str]
    final_report: str
    report_path: Path


@dataclass
class RunState:
    """What phase A (steps 1-3) found, kept so that phase B can continue from it."""

    task_id: str
    topic: str
    run_id: str
    read_papers: list[PaperDocument]
    read_results: list[ReaderResult]
    read_evidence: list[Evidence]
    papers: list[PaperDocument]
    reader_results: list[ReaderResult]
    evidence: list[Evidence]
    unverified: list[UnverifiedClaim]
    corrected: int
    warnings: list[str]
    kept: list[UnverifiedClaim]

async def no_progress(message: str) -> None:
    """The default progress callback: ignores the message."""


async def prepare_run(
    topic: str, settings: SupervisorSettings, memory: RunMemory, progress: Progress = no_progress,
) -> RunState:
    """Phase A, steps 1-3: retrieval, readers, evidence check. Raises RunStopped if the run cannot continue."""
    task_id = f'run-{uuid4().hex[:12]}'
    await memory.start_run(task_id, topic)
    try:
        await progress('Step 1/7: finding papers')
        retrieval, papers, warnings = await retrieve(topic, task_id, settings, memory)
        await progress(f'Step 2/7: reading {len(papers)} papers')
        read_papers, read_results, read_evidence, step2_warnings = await read_all_papers(task_id, papers, settings, memory)
        await progress(f'Step 3/7: checking the claims of {len(read_papers)} papers')
        papers, reader_results, evidence, unverified, corrected, step3_warnings = await check_evidence(
            task_id, read_papers, read_results, read_evidence, settings, memory)
    except RunStopped:
        await memory.finish_run(task_id, 'stopped')
        raise
    except Exception:
        await memory.finish_run(task_id, 'failed')
        raise
    return RunState(
        task_id=task_id, topic=topic, run_id=retrieval.run_id,
        read_papers=read_papers, read_results=read_results, read_evidence=read_evidence,
        papers=papers, reader_results=reader_results, evidence=evidence,
        unverified=unverified, corrected=corrected, warnings=warnings + step2_warnings + step3_warnings, kept=[],
    )

def keep_claims(state: RunState, keep_ids: set[str]) -> RunState:
    """The state with the chosen Unable-to-Verify claims put back; only keepable claims can be kept."""
    keep_ids = keep_ids & {item.claim.claim_id for item in state.unverified if item.keepable}
    if not keep_ids:
        return state
    checked = {claim.claim_id: claim for result in state.reader_results for claim in all_claims(result)}
    wanted = checked.keys() | keep_ids
    papers, reader_results, cited = [], [], set()
    for paper, original in zip(state.read_papers, state.read_results):
        result = original.model_copy(update={
            name: [checked.get(claim.claim_id, claim) for claim in getattr(original, name) if claim.claim_id in wanted]
            for name in CLAIM_FIELDS
        })
        claims = all_claims(result)
        if claims:
            papers.append(paper)
            reader_results.append(result)
            cited |= {evidence_id for claim in claims for evidence_id in claim.evidence_ids}
    return replace(
        state, papers=papers, reader_results=reader_results,
        evidence=[item for item in state.read_evidence if item.evidence_id in cited],
        unverified=[item for item in state.unverified if item.claim.claim_id not in keep_ids],
        kept=[item for item in state.unverified if item.claim.claim_id in keep_ids],
    )


async def complete_run(
    state: RunState, settings: SupervisorSettings, memory: RunMemory, progress: Progress = no_progress,
) -> RunOutput:
    """Phase B, steps 4-7 and the final report. Raises RunStopped if the run cannot continue."""
    task_id = state.task_id
    try:
        await progress('Step 4/7: finding common references')
        references = await find_references(task_id, state.run_id, state.papers, settings, memory)
        await progress('Step 5/7: finding connections and research gaps')
        connections, research_gaps, step5_warnings = await find_connections(
            task_id, state.reader_results, state.evidence, settings, memory)
        await progress('Step 6/7: writing the report')
        draft = await write_draft(task_id, state.topic, state.papers, state.reader_results, state.evidence,
                                  references, connections, research_gaps, settings, memory)
        await progress('Step 7/7: checking coverage')
        draft, step7_warnings = await review_coverage(task_id, draft, settings, memory)
        all_warnings = state.warnings + step5_warnings + step7_warnings
        claims_kept = sum(len(all_claims(result)) for result in state.reader_results)
        final_report = draft.markdown.rstrip() + '\n\n' + supervisor_section(
            state.read_papers, len(state.papers), claims_kept, state.corrected, state.unverified, state.kept, all_warnings)
        report_path = save_report(final_report, settings.reports_path, task_id)
    except RunStopped:
        await memory.finish_run(task_id, 'stopped')
        raise
    except Exception:
        await memory.finish_run(task_id, 'failed')
        raise
    await memory.finish_run(task_id, 'completed', report_id=draft.report_id, revision=draft.revision)
    return RunOutput(
        task_id=task_id,
        topic=state.topic,
        papers=state.papers,
        reader_results=state.reader_results,
        evidence=state.evidence,
        references=references,
        connections=connections,
        research_gaps=research_gaps,
        unverified=state.unverified,
        draft=draft,
        warnings=all_warnings,
        final_report=final_report,
        report_path=report_path,
    )

def keepable_claims(state: RunState) -> list[UnverifiedClaim]:
    """The Unable-to-Verify claims the user may still keep (their quotes are real)."""
    return [item for item in state.unverified if item.keepable]

async def ask_about_claims(state: RunState, memory: RunMemory) -> list[UnverifiedClaim]:
    """Record that the user is asked about the keepable claims, and return them."""
    keepable = keepable_claims(state)
    await memory.record_step(state.task_id, 'user-review', 'working', notes=f'{len(keepable)} claim(s) to decide')
    return keepable

async def apply_decision(state: RunState, keep_ids: set[str], memory: RunMemory) -> RunState:
    """Keep the chosen claims and record the user's decision."""
    keepable = keepable_claims(state)
    state = keep_claims(state, keep_ids)
    await memory.record_step(state.task_id, 'user-review', 'completed',
                             notes=f'{len(state.kept)} kept, {len(keepable) - len(state.kept)} dropped')
    return state

async def keep_none(claims: list[UnverifiedClaim]) -> set[str]:
    """The default decision: keep none of the claims that could not be verified."""
    return set()

async def run(
    topic: str, settings: SupervisorSettings, memory: RunMemory,
    progress: Progress = no_progress, decide: Decide = keep_none,
) -> RunOutput:
    """The whole run: phase A, the user's decision on keepable claims, then phase B. Raises RunStopped if it cannot continue."""
    state = await prepare_run(topic, settings, memory, progress)
    if keepable_claims(state):
        keepable = await ask_about_claims(state, memory)
        state = await apply_decision(state, await decide(keepable), memory)
    return await complete_run(state, settings, memory, progress)