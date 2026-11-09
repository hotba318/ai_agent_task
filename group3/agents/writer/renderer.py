import hashlib
import re
from datetime import date

from .validator import all_claims
from .draft import ReviewedDraft


def text(value):
    value = str(value).replace("\\", "\\\\").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([`*_\[\]#|])", r"\\\1", value).replace("\r", "").replace("\n", "<br>")


def anchor(eid):
    return "ev-" + hashlib.sha256(eid.encode()).hexdigest()[:16]


def render(request, plan, report_id, revision, missing, feedback=None):
    claims = {c.claim_id: c for c in all_claims(request)}
    synthesized=isinstance(plan,ReviewedDraft)
    draft=plan.draft if synthesized else None
    accepted=plan.accepted_ids() if synthesized else set()
    def claim_text(claim):
        citations = " ".join(f"[{text(eid)}](#{anchor(eid)})" for eid in claim.evidence_ids)
        return text(claim.text) + " " + citations
    def paragraphs(ids):
        return "\n\n".join(claim_text(claims[cid]) for cid in ids) or "제공된 근거가 없습니다."
    def prose(values):
        result=[]
        for statement in values:
            if statement.statement_id not in accepted:
                continue
            evidence_ids=list(dict.fromkeys(eid for cid in statement.claim_ids for eid in claims[cid].evidence_ids))
            label="**추론(추가 확인 필요):** " if statement.kind=="inference" else ""
            result.append(label+text(statement.text)+" "+" ".join(f"[{text(eid)}](#{anchor(eid)})" for eid in evidence_ids))
        return "\n\n".join(result) or "제공된 근거로 작성·검토를 통과한 문장이 없습니다."
    parts = [f"# {text(request.topic)} — Literature Review", f"- 생성일: {date.today().isoformat()}\n- 분석 대상 논문 수: {len(request.papers)}\n- 선정 기준: 관련성 우선, 최신성 차순위\n- 보고서 ID: {report_id} / revision {revision}\n- 검증 상태: Supervisor Evidence 검증 대기"]
    if request.data_provenance == "example_fixture":
        parts.append("**예시 데이터 보고서: 실제 원문 발췌를 사용하는 그룹 2 인터페이스 시험용 입력입니다. 그룹 2의 실제 분석 결과가 아닙니다.**")
    if feedback:
        parts.append("Coverage 재작성 요청: " + text(feedback.note) + "\n\n요청 영역: " + text(", ".join(feedback.missing_sections) or "미지정") + "\n\n요청 논문: " + text(", ".join(feedback.missing_paper_ids) or "미지정"))
    parts += ["## 1. Introduction", prose(draft.introduction) if synthesized else paragraphs(plan.introduction), "## 2. Overview of Selected Papers"]
    readers = {r.paper_id: r for r in request.reader_results}
    for paper in request.papers:
        parts.append(f"### {text(paper.title)}\n\n[{text(paper.paper_id)}]({paper.source_url}) / 최초 제출 {paper.submitted_date}")
        reader = readers.get(paper.paper_id)
        if synthesized:
            summary=next((s for s in draft.paper_summaries if s.paper_id==paper.paper_id),None)
            parts.append(prose(summary.paragraphs) if summary else "작성 가능한 논문별 요약 근거가 없습니다.")
        else:
            parts.append(paragraphs([c.claim_id for c in reader.overview]) if reader else "Reader 입력이 없습니다.")
    parts.append("## 3. Comparative Analysis")
    if synthesized:
        parts.append(prose(draft.comparison))
        parts.append("아래 표는 Reader 입력과 인용 위치를 보존한 자료이며, 원문 함의는 Supervisor 검증 대기 상태입니다.")
    table = ["| 논문 | 방법론 | 데이터셋 | 주요 결과 |", "|---|---|---|---|"]
    for paper in request.papers:
        reader = readers.get(paper.paper_id)
        cells = [text(paper.paper_id)]
        for field in ("methods", "datasets", "results"):
            values = getattr(reader, field) if reader else []
            cells.append("<br><br>".join(claim_text(c) for c in values) or "입력 근거 없음")
        table.append("| " + " | ".join(cells) + " |")
    parts.append("\n".join(table))
    parts.append("## 4. Common References")
    parts.append("집계 기준: 선정 논문 중 서로 다른 인용 논문 수. 단일 논문 내 반복 인용은 한 번으로 집계합니다.")
    if request.common_references.common_references:
        table = ["| 문헌 | 인용 논문 수 | 인용한 선정 논문 |", "|---|---:|---|"]
        for ref in request.common_references.common_references:
            label = ref.title or ref.occurrences[0].raw_text
            table.append(f"| {text(label)} | {ref.cited_by_count} | {text(', '.join(ref.cited_by_paper_ids))} |")
        parts.append("\n".join(table))
    else:
        parts.append("추출된 참고문헌에서 조건을 충족한 공통 문헌이 없습니다. 추출 누락 가능성은 별도 확인해야 합니다.")
    if request.common_references.possible_duplicates:
        parts.append(f"동일 문헌 여부가 불확실한 후보 {len(request.common_references.possible_duplicates)}쌍은 임의 통합하지 않았습니다.")
    parts.append("## 5. Connections and Conflicts")
    if synthesized:
        parts.append(prose(draft.connections))
    for connection in request.connections:
        parts.append(f"### {text(connection.kind)} — {text(connection.connection_id)}")
        parts.extend(claim_text(c) for c in connection.claims)
    if not request.connections:
        parts.append("연결/상충 분석 입력이 없습니다. 결과를 추정하지 않습니다.")
    parts += ["## 6. Research Gaps", prose(draft.research_gaps) if synthesized else paragraphs(plan.research_gaps), "## 7. Limitations", prose(draft.limitations) if synthesized else paragraphs(plan.limitations),
        "구조·인용 위치 검증은 사실 검증을 대체하지 않습니다. 주장의 원문 함의와 상충 여부는 Supervisor/Reader가 확인해야 합니다."]
    if synthesized:
        withheld=[a for a in plan.review.assessments if a.verdict!="supported"]
        parts.append(f"모델 근거 검토에서 {len(withheld)}개, 프로그램 수치 검사에서 {len(plan.programmatic_rejections)}개 문장을 보류했습니다. 통과 문장도 최종 사실 검증 완료를 의미하지 않습니다.")
    if missing:
        parts.append("미충족 영역:\n\n" + "\n".join("- " + text(v) for v in missing))
    parts += ["## 8. References"]
    parts.extend(f"- [{text(p.title)}]({p.source_url}) — {text(p.paper_id)}" for p in request.papers)
    for ref in request.common_references.common_references:
        url = "https://doi.org/" + ref.doi if ref.doi else "https://arxiv.org/abs/" + ref.arxiv_id.removeprefix("arxiv:") if ref.arxiv_id else None
        label = text(ref.title or ref.reference_id)
        parts.append(f"- [{label}]({url})" if url else "- " + label + " — " + text(ref.occurrences[0].raw_text))
    parts.append("### Evidence Map")
    for evidence in request.evidence:
        paper = next(p for p in request.papers if p.paper_id == evidence.paper_id)
        section = next(s for s in paper.sections if s.section_id == evidence.section_id)
        parts.append(f'<a id="{anchor(evidence.evidence_id)}"></a>\n\n- {text(evidence.evidence_id)}: [{text(evidence.paper_id)} / {text(evidence.section_id)}]({section.source_url})\n  - 원문 위치: {text(section.source_locator)}\n  - 발췌: {text(evidence.quote)}')
    return "\n\n".join(parts) + "\n"
