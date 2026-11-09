"""Grounded prose and explicit support review, not a claim ordering list."""
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .validator import validate_input


class StrictModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class Statement(StrictModel):
    statement_id: str
    text: str
    claim_ids: list[str]
    kind: Literal["supported","inference"]


class PaperSummary(StrictModel):
    paper_id: str
    paragraphs: list[Statement]


class GroundedDraft(StrictModel):
    introduction: list[Statement]
    paper_summaries: list[PaperSummary]
    comparison: list[Statement]
    connections: list[Statement]
    research_gaps: list[Statement]
    limitations: list[Statement]


class SupportAssessment(StrictModel):
    statement_id: str
    verdict: Literal["supported","unsupported","uncertain"]
    reason: str


class SupportReview(StrictModel):
    assessments: list[SupportAssessment]


@dataclass
class ReviewedDraft:
    draft: GroundedDraft
    review: SupportReview
    decisions: list[dict] = field(default_factory=list)
    model_calls: int = 0
    programmatic_rejections: list[dict] = field(default_factory=list)

    def accepted_ids(self):
        return {a.statement_id for a in self.review.assessments if a.verdict=="supported"}


class UnsupportedNumericError(ValueError):
    def __init__(self,statement_id,unexpected):
        self.statement_id=statement_id
        super().__init__(f"unsupported numeric assertion: {statement_id}; remove unsupported values {','.join(str(v) for v in sorted(unexpected))} or cite the provided claims that contain them")


def statements(draft):
    result=[]
    for name in ("introduction","comparison","connections","research_gaps","limitations"):
        result.extend((name,s) for s in getattr(draft,name))
    for summary in draft.paper_summaries:
        result.extend(("overview:"+summary.paper_id,s) for s in summary.paragraphs)
    return result


def numbers(value):
    return {Decimal(v.replace(",","")) for v in re.findall(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?",value)}


def validate_draft(draft,request,require_coverage=True):
    claims=validate_input(request)
    evidence={e.evidence_id:e for e in request.evidence}
    ids=set()
    summaries=[p.paper_id for p in draft.paper_summaries]
    if len(summaries)!=len(set(summaries)) or set(summaries)-{p.paper_id for p in request.papers}:
        raise ValueError("duplicate or unknown summary paper")
    limitation_ids={c.claim_id for r in request.reader_results for c in r.limitations}
    gap_ids={c.claim_id for c in request.research_gaps}
    if require_coverage and any(r.overview for r in request.reader_results) and not draft.introduction:
        raise ValueError("introduction required when overview evidence is available")
    compared={r.paper_id for r in request.reader_results if r.methods or r.datasets or r.results}
    comparison_ids={c.claim_id for r in request.reader_results for name in ("methods","datasets","results") for c in getattr(r,name)}
    if require_coverage and len(compared)>=2 and not draft.comparison:
        raise ValueError("comparative synthesis required when multiple analyzed papers are available")
    if require_coverage and limitation_ids and not draft.limitations:
        raise ValueError("limitations required when limitation evidence is available")
    if require_coverage and gap_ids and not draft.research_gaps:
        raise ValueError("research gaps required when gap evidence is available")
    if require_coverage and request.connections and not draft.connections:
        raise ValueError("connections required when connection evidence is available")
    supplied_summary={s.paper_id:s for s in draft.paper_summaries}
    for reader in request.reader_results:
        if require_coverage and any(getattr(reader,name) for name in ("overview","methods","datasets","results","limitations")):
            if reader.paper_id not in supplied_summary or not supplied_summary[reader.paper_id].paragraphs:
                raise ValueError("summary required for each paper with Reader evidence")
    conflicts=[{c.claim_id for c in relation.claims} for relation in request.connections if relation.kind=="conflict"]
    for section,s in statements(draft):
        if not s.statement_id.strip() or s.statement_id in ids:
            raise ValueError("duplicate/blank statement ID")
        ids.add(s.statement_id)
        if not s.text.strip() or not s.claim_ids or len(set(s.claim_ids))!=len(s.claim_ids) or set(s.claim_ids)-claims.keys():
            raise ValueError(f"statement must cite supplied claims: {s.statement_id}")
        if re.search(r"https?://|www\.",s.text,re.I):
            raise ValueError("URLs must be rendered from source metadata, not generated prose")
        source=" ".join(claims[cid].text+" "+" ".join(evidence[eid].quote for eid in claims[cid].evidence_ids) for cid in s.claim_ids)
        if numbers(s.text)-numbers(source):
            raise UnsupportedNumericError(s.statement_id,numbers(s.text)-numbers(source))
        cited_papers={evidence[eid].paper_id for cid in s.claim_ids for eid in claims[cid].evidence_ids}
        if any(set(s.claim_ids)&group and not group<=set(s.claim_ids) for group in conflicts):
            raise ValueError("conflict synthesis must retain both sides' claims")
        if section.startswith("overview:") and cited_papers!={section.removeprefix("overview:")}:
            raise ValueError("paper summary cites another paper")
        if section=="comparison" and len(compared)>=2 and len(cited_papers)<2:
            raise ValueError("comparative synthesis must cite at least two analyzed papers")
        if section=="comparison" and not set(s.claim_ids)<=comparison_ids:
            raise ValueError("comparison must cite supplied method/dataset/result claims")
        if section=="limitations" and not set(s.claim_ids)<=limitation_ids:
            raise ValueError("limitation is not grounded in supplied limitations")
        if section=="research_gaps":
            if not set(s.claim_ids)&gap_ids and (s.kind!="inference" or not set(s.claim_ids)<=limitation_ids):
                raise ValueError("new gap requires supplied limitations and an inference label")
            if gap_ids and not set(s.claim_ids)<=gap_ids|limitation_ids:
                raise ValueError("gap must cite supplied gaps/limitations")
        if section=="connections" and not request.connections and (s.kind!="inference" or len(cited_papers)<2):
            raise ValueError("derived connection requires two papers and an inference label")


def validate_review(review,draft):
    expected={s.statement_id for _,s in statements(draft)}
    actual=[a.statement_id for a in review.assessments]
    if set(actual)!=expected or len(actual)!=len(set(actual)):
        raise ValueError("support reviewer must assess every generated statement exactly once")


def draft_coverage(plan,request):
    accepted=plan.accepted_ids()
    missing=[]
    for field in ("introduction","comparison","connections","research_gaps","limitations"):
        if not any(s.statement_id in accepted for s in getattr(plan.draft,field)):
            missing.append("draft:"+field)
    summaries={p.paper_id:p for p in plan.draft.paper_summaries}
    for paper in request.papers:
        if paper.paper_id not in summaries or not any(s.statement_id in accepted for s in summaries[paper.paper_id].paragraphs):
            missing.append("draft:overview:"+paper.paper_id)
    missing.extend("support_review:"+a.statement_id for a in plan.review.assessments if a.verdict!="supported")
    missing.extend("programmatic_review:"+a["statement_id"] for a in plan.programmatic_rejections)
    return missing


def withhold_unsupported_numbers(draft,request):
    rejected=[]
    draft=draft.model_copy(deep=True)
    while True:
        try:
            validate_draft(draft,request,require_coverage=False)
            return draft,rejected
        except UnsupportedNumericError as exc:
            rejected.extend({"statement_id":s.statement_id,"text":s.text,"claim_ids":s.claim_ids,"reason":str(exc)} for _,s in statements(draft) if s.statement_id==exc.statement_id)
            for name in ("introduction","comparison","connections","research_gaps","limitations"):
                setattr(draft,name,[s for s in getattr(draft,name) if s.statement_id!=exc.statement_id])
            for summary in draft.paper_summaries:
                summary.paragraphs=[s for s in summary.paragraphs if s.statement_id!=exc.statement_id]
