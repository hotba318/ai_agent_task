"""Explicit live evolution checks. Controlled replanning observation is labelled as such."""
import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

from group3.agents.references.agent import CommonReferencesAgent
from group3.agents.retrieval.planner import GroqRetrievalPlanner, SearchObservation
from group3.agents.writer.state import RevisionLimitError, WriterState
from group3.common.analysis_schemas import CoverageFeedback, RevisionRequest, WriterRequest, WriterResult
from group3.common.config import AnalysisSettings
from group3.services import write_report


async def run(args):
    original=json.loads(args.initial_result.read_text(encoding="utf-8"))
    initial=WriterResult.model_validate(original.get("result",original))
    settings=AnalysisSettings()
    settings.writer_mode="groq"
    settings.output_root=Path(initial.markdown_path).parents[2]
    if not settings.groq_api_key or not settings.groq_api_key.get_secret_value().strip():
        raise ValueError("GROQ_API_KEY is required")
    state=WriterState(settings.output_root/"writer-state.sqlite3")
    with state.connect() as db:
        row=db.execute("SELECT request FROM reports WHERE id=?",(initial.report_id,)).fetchone()
    if row is None:
        raise ValueError("initial report request was not found")
    request=WriterRequest.model_validate_json(row[0])
    feedback=CoverageFeedback(missing_sections=["introduction","comparison"],note=
        "Introduction은 원문이 입증하는 범위로 제한하세요. 단일 에이전트 대비 우월성을 입증되지 않은 일반 사실로 서술하지 마세요. "
        "제공된 Reader의 방법론/결과를 두 편 이상 원문 근거로 비교하는 문장을 추가하세요. 데이터가 없는 부분은 채우지 마세요.")
    revision=RevisionRequest(report_id=initial.report_id,feedback=feedback)
    result=await write_report(revision,settings)
    audit=json.loads(Path(result.decisions_path).read_text(encoding="utf-8"))
    assert result.revision==1 and audit["previous_report_supplied"] and result.model_calls>=2
    assert Path(initial.markdown_path).exists() and Path(result.markdown_path).exists()
    limited=False
    try:
        await write_report(revision,settings)
    except RevisionLimitError:
        limited=True
    assert limited
    draft=json.loads(Path(result.draft_path).read_text(encoding="utf-8"))
    old=json.loads(Path(initial.draft_path).read_text(encoding="utf-8")) if initial.draft_path else None
    assert draft["comparison"], "Supplied analyses must produce comparative synthesis"
    review=json.loads(Path(result.review_path).read_text(encoding="utf-8"))
    assert any(a["verdict"]=="supported" for a in review["assessments"])
    # Test the actual model's next-action decision without pretending the controlled
    # scarcity observation was a real failed search. All example papers are real inputs.
    observation=SearchObservation(1,request.topic,9,1,1,1,1,0,None,[{
        "paper_id":request.papers[0].paper_id,"title":request.papers[0].title,
        "abstract":(request.papers[0].abstract or "")[:350]}])
    from group3.common.schemas import RetrievalRequest
    retrieval=RetrievalRequest(task_id="controlled-live-plan",topic=request.topic,target_papers=3,minimum_papers=3)
    async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
        planner=GroqRetrievalPlanner(client,settings.groq_api_key.get_secret_value(),settings.groq_model)
        action=await planner.decide(retrieval,observation,[observation])
    refs=CommonReferencesAgent().analyze(request.papers,request.task_id)
    record={"tested_at":datetime.now(timezone.utc).isoformat(),"input_provenance":request.data_provenance,
        "actual_groq_called":True,"writer_revision":result.model_dump(mode="json"),
        "previous_report_supplied":True,"second_coverage_rewrite_rejected":limited,
        "generated_prose_changed":old!=draft,
        "retrieval_model_decision":{"observation_kind":"controlled_scarcity_not_actual_failed_search","observation":asdict(observation),
            "decision":asdict(action),"decision_executed_as_search":False},
        "reference_analysis":refs.model_dump(mode="json"),"supervisor_fact_verification":False}
    serialized=json.dumps(record,ensure_ascii=False,indent=2)
    assert settings.groq_api_key.get_secret_value() not in serialized
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(serialized,encoding="utf-8")
    Path("examples/agent-evolution-report.md").write_text(result.markdown,encoding="utf-8")
    print(f"Evolution live checks passed: revision={result.revision}, model_calls={result.model_calls}, repeat_rewrite_rejected={limited}")
    print(f"Retrieval model decision on controlled observation: {action.action}; real references: {len(refs.common_references)}")
    print(f"Record: {args.output}; report: examples/agent-evolution-report.md")


def main():
    parser=argparse.ArgumentParser(description="Live grounded revision plus controlled retrieval model decision (Groq usage applies)")
    parser.add_argument("--initial-result",type=Path,default=Path("docs/test-results/groq-live-result.json"))
    parser.add_argument("--output",type=Path,default=Path("docs/test-results/agent-evolution-live.json"))
    asyncio.run(run(parser.parse_args()))


if __name__=="__main__":
    main()
