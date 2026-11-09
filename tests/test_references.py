from group3.agents.references.agent import CommonReferencesAgent
from group3.agents.references.matcher import normalize_arxiv, normalize_doi
from group3.common.analysis_schemas import ReferencesRequest
from group3.common.schemas import PaperDocument, Reference, Section
from group3.agents.retrieval.storage import JsonPaperStore
import pytest


def document(metadata, refs):
    return PaperDocument(**metadata.model_dump(), parse_method="arxiv_html", raw_document_path="fixture",
        parsed_document_path="fixture", raw_sha256="f"*64,
        sections=[Section(section_id="s1", title="Fixture", text="Synthetic evidence body", source_locator="/fixture", source_url=metadata.html_url)], references=refs)


def reference(key="r1", **kwargs):
    return Reference(reference_id=key, raw_text=kwargs.pop("raw_text", key + " synthetic reference"), source_locator="/fixture/"+key, **kwargs)


def test_normalization():
    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("DOI: 10.1234/a(b)") == "10.1234/a(b)"
    assert normalize_doi("10.1234/test).") == "10.1234/test"
    assert normalize_doi("not-a-doi") is None
    assert normalize_arxiv("https://arxiv.org/abs/2401.12345v2") == "arxiv:2401.12345"


def test_distinct_counts_and_order(make_paper):
    papers = [document(make_paper(1), [reference(doi="10.1234/A"), reference("repeat", doi="https://doi.org/10.1234/a"), reference("b", arxiv_id="2401.12345v1")]),
              document(make_paper(2), [reference(doi="doi:10.1234/a"), reference("b", arxiv_id="arxiv:2401.12345v2")]),
              document(make_paper(3), [reference(doi="10.1234/a"), reference("unique", doi="10.1234/only")])]
    result = CommonReferencesAgent().analyze(papers, "test")
    assert [r.cited_by_count for r in result.common_references] == [3, 2]
    assert len(result.common_references[0].occurrences) == 4
    assert result.common_references[0].reference_id == "doi:10.1234/a"


def test_strong_identifier_bridge_and_conflict(make_paper):
    papers = [document(make_paper(1), [reference(doi="10.1234/a", arxiv_id="2401.12345")]),
              document(make_paper(2), [reference(doi="10.1234/a")]),
              document(make_paper(3), [reference(arxiv_id="2401.12345")]),
              document(make_paper(4), [reference(doi="10.1234/different", arxiv_id="2401.12345")])]
    result = CommonReferencesAgent().analyze(papers, "test")
    assert len(result.common_references) == 1
    assert result.common_references[0].cited_by_count == 3
    assert any(p.reason == "conflicting_identifiers" for p in result.possible_duplicates)


def test_metadata_fallback_and_ambiguous_title(make_paper):
    common = dict(authors=["A. Fixture"], year=2024)
    papers = [document(make_paper(1), [reference(title="Some: Research! Title", raw_text="citation A", **common)]),
              document(make_paper(2), [reference(title="some research title", raw_text="citation B", **common)]),
              document(make_paper(3), [reference(title="Some research title", raw_text="citation C")])]
    result = CommonReferencesAgent().analyze(papers, "test")
    assert result.common_references[0].cited_by_count == 2
    assert result.common_references[0].reference_id.startswith("local:")
    assert result.possible_duplicates


def test_empty_and_threshold(make_paper):
    papers = [document(make_paper(1), []), document(make_paper(2), [reference(doi="10.1234/a")])]
    result = CommonReferencesAgent().analyze(papers, "test")
    assert result.common_references == [] and result.warnings
    with pytest.raises(ValueError):
        CommonReferencesAgent().analyze(papers, "test", minimum=1)
    with pytest.raises(ValueError):
        CommonReferencesAgent().analyze([papers[0], papers[0]], "test")


def test_identifier_free_exact_citation_and_tie_order(make_paper):
    raw = "Fixture Author (2024). A complete long citation for an offline reference test."
    papers = [document(make_paper(1), [reference(raw_text=raw+" Cited by: Section 1"), reference("b",doi="10.1234/b")]),
              document(make_paper(2), [reference(raw_text=raw+" Cited by: Section 7"), reference("b",doi="10.1234/b")])]
    forward = CommonReferencesAgent().analyze(papers,"test")
    reverse = CommonReferencesAgent().analyze(list(reversed(papers)),"test")
    assert len(forward.common_references) == 2
    assert forward.common_references == reverse.common_references


def test_three_citing_threshold(make_paper):
    papers = [document(make_paper(i),[reference(doi="10.1234/a")]) for i in (1,2)]
    assert not CommonReferencesAgent().analyze(papers,"test",minimum=3).common_references


def test_store_selected_subset(tmp_path, make_paper):
    from group3.common.schemas import RetrievalResult
    store = JsonPaperStore(tmp_path)
    folder = store.begin("test", "run")
    papers = [document(make_paper(i), [reference(doi="10.1234/a")]) for i in (1,2,3)]
    for p in papers:
        store.save(folder, p)
    store.finish(folder, RetrievalResult(task_id="test", run_id="run", status="completed", requested_count=3, selected_count=3, paper_store_uri=folder.as_uri(), paper_ids=[p.paper_id for p in papers]))
    request = ReferencesRequest(task_id="test", run_id="run", paper_ids=[p.paper_id for p in papers[:2]])
    result = CommonReferencesAgent().run(request, store, folder)
    assert result.common_references[0].cited_by_count == 2
    with pytest.raises(ValueError, match="not in the selected manifest"):
        CommonReferencesAgent().run(request.model_copy(update={"paper_ids": ["arxiv:2401.99999"]}), store, folder)
