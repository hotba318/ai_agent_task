from group3.common.analysis_schemas import CommonReference, PossibleDuplicate, ReferencesRequest, ReferencesResult
from group3.common.interfaces import PaperStore
from group3.common.schemas import PaperDocument
from .matcher import item, match, stable_local_id


class CommonReferencesAgent:
    def analyze(self, papers: list[PaperDocument], task_id: str, minimum=2) -> ReferencesResult:
        if minimum < 2:
            raise ValueError("common references require at least two citing papers")
        if len({p.paper_id for p in papers}) != len(papers):
            raise ValueError("duplicate selected paper IDs")
        entries = [item(p.paper_id, ref) for p in sorted(papers, key=lambda p: p.paper_id)
                   for ref in sorted(p.references, key=lambda r: (r.reference_id, r.raw_text))]
        groups, ambiguous = match(entries)
        common, warnings, seen_ids = [], [], set()
        for group in groups:
            citing = sorted({entry.occurrence.paper_id for entry in group})
            if len(citing) < minimum:
                continue
            dois = sorted({e.doi for e in group if e.doi})
            arxivs = sorted({e.arxiv for e in group if e.arxiv})
            identifier = "doi:" + dois[0] if dois else arxivs[0] if arxivs else stable_local_id(group[0].fingerprint)
            if identifier in seen_ids:
                identifier += ":" + stable_local_id(repr([e.occurrence.model_dump() for e in group])).split(":")[1]
            seen_ids.add(identifier)
            common.append(CommonReference(reference_id=identifier, title=next((e.ref.title for e in group if e.ref.title), None),
                doi=dois[0] if dois else None, arxiv_id=arxivs[0] if arxivs else None,
                cited_by_count=len(citing), cited_by_paper_ids=citing, occurrences=[e.occurrence for e in group]))
        for paper in papers:
            if not paper.references:
                warnings.append(f"{paper.paper_id}: no extracted references; shared citations may be missed")
        common.sort(key=lambda ref: (-ref.cited_by_count, ref.reference_id))
        review=bool(ambiguous or any(not p.references for p in papers))
        decisions=[{"action":"assess_input_quality","selected_papers":len(papers),"reference_occurrences":len(entries),
            "occurrences_without_strong_id":sum(not e.doi and not e.arxiv for e in entries)},
            {"action":"resolve_identity","exact_groups":len(groups),"unresolved_pairs":len(ambiguous),"policy":"uncertain identities kept separate; no guessed merge"},
            {"action":"request_review" if review else "return_result","reason":"Unresolved identity or missing bibliography" if review else "No unresolved identity/missing bibliography detected","fact_verification":"not_performed"}]
        if review:
            warnings.append("Reference identity/bibliography review required; counts include only conservatively matched groups.")
        return ReferencesResult(task_id=task_id, paper_ids=[p.paper_id for p in papers],
            common_references=common, possible_duplicates=[PossibleDuplicate(left=a, right=b, reason=r) for a,b,r in ambiguous],
            minimum_citing_papers=minimum, warnings=warnings,review_required=review,decisions=decisions)

    def run(self, request: ReferencesRequest, store: PaperStore, folder) -> ReferencesResult:
        papers = store.list_papers(folder)
        if request.paper_ids:
            if len(request.paper_ids) != len(set(request.paper_ids)):
                raise ValueError("duplicate requested paper IDs")
            lookup = {p.paper_id: p for p in papers}
            if set(request.paper_ids) - lookup.keys():
                raise ValueError("requested paper is not in the selected manifest")
            papers = [lookup[pid] for pid in request.paper_ids]
        return self.analyze(papers, request.task_id, request.min_citing_papers)
