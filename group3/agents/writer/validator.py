from group3.common.analysis_schemas import WriterRequest


def all_claims(request: WriterRequest):
    claims = []
    for reader in request.reader_results:
        for field in ("overview", "methods", "datasets", "results", "limitations"):
            claims.extend(getattr(reader, field))
    for connection in request.connections:
        claims.extend(connection.claims)
    return claims + request.research_gaps


def validate_input(request: WriterRequest):
    papers = {p.paper_id: p for p in request.papers}
    if len(papers) != len(request.papers):
        raise ValueError("duplicate paper IDs")
    if not request.topic.strip():
        raise ValueError("blank topic")
    readers = {r.paper_id: r for r in request.reader_results}
    if len(readers) != len(request.reader_results) or readers.keys() - papers.keys():
        raise ValueError("duplicate or unknown Reader paper")
    evidence = {e.evidence_id: e for e in request.evidence}
    if len(evidence) != len(request.evidence):
        raise ValueError("duplicate evidence IDs")
    for entry in evidence.values():
        paper = papers.get(entry.paper_id)
        if paper is None:
            raise ValueError("evidence points to unknown paper")
        sections = {s.section_id: s for s in paper.sections}
        if len(sections) != len(paper.sections):
            raise ValueError("duplicate section IDs")
        section = sections.get(entry.section_id)
        if section is None or not entry.quote.strip() or entry.quote not in section.text:
            raise ValueError(f"evidence quote not found in supplied paper section: {entry.evidence_id}")
    claims = all_claims(request)
    if len({c.claim_id for c in claims}) != len(claims):
        raise ValueError("duplicate claim IDs")
    for claim in claims:
        if not claim.text.strip() or set(claim.evidence_ids) - evidence.keys():
            raise ValueError(f"claim has invalid evidence: {claim.claim_id}")
    for reader in request.reader_results:
        for field in ("overview", "methods", "datasets", "results", "limitations"):
            for claim in getattr(reader, field):
                if any(evidence[eid].paper_id != reader.paper_id for eid in claim.evidence_ids):
                    raise ValueError("Reader claim cites another paper")
    for connection in request.connections:
        if connection.kind == "conflict":
            cited = {evidence[eid].paper_id for claim in connection.claims for eid in claim.evidence_ids}
            if len(connection.claims) < 2 or len(cited) < 2:
                raise ValueError("conflict requires two claims and two cited papers")
    refs = request.common_references
    if refs.task_id != request.task_id or set(refs.paper_ids) != papers.keys():
        raise ValueError("reference analysis task/selected paper set mismatch")
    # Verify the references against original selected-paper occurrences, not just counts.
    for ref in refs.common_references:
        if ref.cited_by_count < refs.minimum_citing_papers:
            raise ValueError("reference below common citation threshold")
        for occurrence in ref.occurrences:
            paper = papers.get(occurrence.paper_id)
            if paper is None or not any(r.reference_id == occurrence.reference_id
                and r.raw_text == occurrence.raw_text and r.source_locator == occurrence.source_locator for r in paper.references):
                raise ValueError("common reference occurrence not found in supplied papers")
    # Prevent a valid occurrence list from laundering an invented title/identifier/group.
    from group3.agents.references.agent import CommonReferencesAgent
    expected = CommonReferencesAgent().analyze(request.papers, request.task_id, refs.minimum_citing_papers)
    if refs.common_references != expected.common_references:
        raise ValueError("common reference metadata or grouping disagrees with selected-paper analysis")
    return {c.claim_id: c for c in claims}


def missing_coverage(request: WriterRequest):
    missing = []
    readers = {r.paper_id: r for r in request.reader_results}
    for paper in request.papers:
        reader = readers.get(paper.paper_id)
        if reader is None:
            missing.append(f"reader:{paper.paper_id}")
        else:
            for field in ("overview", "methods", "datasets", "results", "limitations"):
                if not getattr(reader, field):
                    missing.append(f"{field}:{paper.paper_id}")
    if not request.connections:
        missing.append("connections")
    if not request.research_gaps:
        missing.append("research_gaps")
    return missing
