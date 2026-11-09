"""Synthetic model outputs for offline control-flow and grounding tests."""
from group3.agents.writer.draft import GroundedDraft, PaperSummary, Statement, SupportAssessment, SupportReview, statements


def mock_draft(request):
    def s(identifier,text,ids,kind="supported"):
        return Statement(statement_id=identifier,text=text,claim_ids=ids,kind=kind)
    over=[r.overview[0].claim_id for r in request.reader_results if r.overview]
    methods=[r.methods[0].claim_id for r in request.reader_results if r.methods]
    limits=[r.limitations[0].claim_id for r in request.reader_results if r.limitations]
    return GroundedDraft(introduction=[s("intro","근거를 종합한 초안입니다.",over)] if over else [],
        paper_summaries=[PaperSummary(paper_id=r.paper_id,paragraphs=[s(f"summary-{i}","제공된 논문 내용을 요약했습니다.",[r.overview[0].claim_id])]) for i,r in enumerate(request.reader_results) if r.overview],
        comparison=[s("compare","제공된 방법을 비교했습니다.",methods)] if methods else [],
        connections=[s("connection","상충하는 양측 주장을 구분해 보존합니다.",[c.claim_id for conn in request.connections for c in conn.claims])] if request.connections else [],
        research_gaps=[s("gap","제공된 연구 공백을 정리했습니다.",[c.claim_id for c in request.research_gaps])] if request.research_gaps else [],
        limitations=[s("limit","제공된 한계에 따라 결과를 해석해야 합니다.",limits)] if limits else [])


def supported_review(draft):
    return SupportReview(assessments=[SupportAssessment(statement_id=s.statement_id,verdict="supported",reason="Synthetic review fixture") for _,s in statements(draft)])
