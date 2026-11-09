import json
from pathlib import Path
from uuid import uuid4

from group3.common.analysis_schemas import RevisionRequest, WriterRequest, WriterResult
from .planner import Planner, validate_plan
from .renderer import render
from .state import WriterState
from .validator import missing_coverage, validate_input
from .draft import ReviewedDraft, draft_coverage


class WriterAgent:
    def __init__(self, planner: Planner, output_root: Path):
        self.planner, self.output_root = planner, output_root.resolve()
        self.state = WriterState(self.output_root / "writer-state.sqlite3")

    async def run(self, request: WriterRequest) -> WriterResult:
        validate_input(request)
        report_id = uuid4().hex
        result = await self._write(request, report_id, 0)
        self.state.create(report_id, request, result)
        return result

    async def revise(self, revision: RevisionRequest) -> WriterResult:
        request = self.state.reserve_revision(revision.report_id)
        # Reservation consumes the one permitted attempt even if upstream generation fails.
        if revision.updated_input is not None:
            updated = revision.updated_input
            if (updated.task_id, updated.topic, updated.data_provenance) != (request.task_id, request.topic, request.data_provenance) or updated.papers != request.papers:
                raise ValueError("Coverage update must preserve original task, topic, provenance and source papers")
            request = updated
        validate_input(request)
        previous=self.state.previous_report(revision.report_id)
        old_path=self.output_root/revision.report_id/"revision-0"/"report.md"
        if previous is None and old_path.is_file():
            previous=old_path.read_text(encoding="utf-8")
        return await self._write(request, revision.report_id, 1, revision.feedback, previous)

    async def _write(self, request, report_id, revision, feedback=None, previous_report=None):
        if feedback and set(feedback.missing_paper_ids)-{p.paper_id for p in request.papers}:
            raise ValueError("Coverage feedback contains unknown paper IDs")
        plan = await self.planner.plan(request, feedback, previous_report=previous_report)
        validate_plan(plan, request)
        missing = missing_coverage(request)
        if isinstance(plan,ReviewedDraft):
            missing.extend(draft_coverage(plan,request))
        generated_warnings=[]
        if isinstance(plan,ReviewedDraft):
            withheld=sum(a.verdict!="supported" for a in plan.review.assessments)+len(plan.programmatic_rejections)
            if withheld:
                generated_warnings.append(f"Withheld {withheld} generated statement(s) after support/numeric checks; inspect support-review.json and decisions.json. Supervisor verification remains pending.")
        if feedback:
            known = {p.paper_id for p in request.papers}
            if set(feedback.missing_paper_ids) - known:
                raise ValueError("Coverage feedback contains unknown paper IDs")
            # Rewriting cannot invent missing upstream inputs. Fixed report sections always render.
        markdown = render(request, plan, report_id, revision, missing, feedback)
        folder = self.output_root / report_id / f"revision-{revision}"
        folder.mkdir(parents=True, exist_ok=False)
        markdown_path, evidence_path = folder / "report.md", folder / "evidence.json"
        markdown_path.write_text(markdown, encoding="utf-8")
        evidence_path.write_text(json.dumps({"schema_version": "0.1", "report_id": report_id,
            "revision": revision, "data_provenance": request.data_provenance, "evidence_verified": False,
            "evidence": [e.model_dump() for e in request.evidence],
            "claims": {c.claim_id: c.model_dump() for c in validate_input(request).values()},
            "common_references": request.common_references.model_dump(),
            "coverage_feedback": feedback.model_dump() if feedback else None}, ensure_ascii=False, indent=2), encoding="utf-8")
        audit={"draft_path":None,"review_path":None,"decisions_path":str(folder/"decisions.json")}
        if isinstance(plan,ReviewedDraft):
            for name,model in (("draft",plan.draft),("support-review",plan.review)):
                path=folder/(name+".json")
                path.write_text(model.model_dump_json(indent=2),encoding="utf-8")
                audit["draft_path" if name=="draft" else "review_path"]=str(path)
            decisions=plan.decisions
        else:
            decisions=[{"action":"extractive_render","generated_prose":False}]
        (folder/"decisions.json").write_text(json.dumps({"revision":revision,"previous_report_supplied":previous_report is not None,
            "coverage_feedback":feedback.model_dump() if feedback else None,"decisions":decisions},ensure_ascii=False,indent=2),encoding="utf-8")
        result = WriterResult(task_id=request.task_id, report_id=report_id, revision=revision,
            status="coverage_incomplete" if missing else "needs_review", markdown_path=str(markdown_path),
            evidence_path=str(evidence_path), markdown=markdown, missing_coverage=missing,
            warnings=["Supervisor Evidence validation is pending; structural checks do not establish truth."] + request.common_references.warnings + generated_warnings,
            mode=self.planner.mode,model_calls=plan.model_calls if isinstance(plan,ReviewedDraft) else 0,**audit)
        (folder / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result
