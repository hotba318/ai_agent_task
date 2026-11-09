"""Provisional Group 1/2 contracts; replace at adapter boundary after team agreement."""
from typing import Literal

from pydantic import Field, model_validator

from .schemas import Contract, PaperDocument


class StoreSelection(Contract):
    task_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    run_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    paper_ids: list[str] = Field(default_factory=list)


class ReferencesRequest(StoreSelection):
    min_citing_papers: int = Field(default=2, ge=2)


class ReferenceOccurrence(Contract):
    paper_id: str
    reference_id: str
    source_locator: str
    raw_text: str


class CommonReference(Contract):
    reference_id: str
    title: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    cited_by_count: int = Field(ge=2)
    cited_by_paper_ids: list[str]
    occurrences: list[ReferenceOccurrence]

    @model_validator(mode="after")
    def count_matches(self):
        ids = set(self.cited_by_paper_ids)
        if self.cited_by_count != len(ids) or len(ids) != len(self.cited_by_paper_ids):
            raise ValueError("cited_by_count must count distinct papers")
        if ids != {o.paper_id for o in self.occurrences}:
            raise ValueError("occurrence papers disagree with citing papers")
        return self


class PossibleDuplicate(Contract):
    left: ReferenceOccurrence
    right: ReferenceOccurrence
    reason: str


class ReferencesResult(Contract):
    task_id: str
    paper_ids: list[str]
    common_references: list[CommonReference]
    possible_duplicates: list[PossibleDuplicate] = Field(default_factory=list)
    ranking_basis: Literal["distinct_selected_papers_citing_reference"] = "distinct_selected_papers_citing_reference"
    minimum_citing_papers: int = Field(default=2, ge=2)
    warnings: list[str] = Field(default_factory=list)
    review_required: bool = False
    decisions: list[dict] = Field(default_factory=list)


class Evidence(Contract):
    evidence_id: str = Field(min_length=1)
    paper_id: str
    section_id: str
    quote: str = Field(min_length=1)


class Claim(Contract):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class ReaderResult(Contract):
    paper_id: str
    overview: list[Claim] = Field(default_factory=list)
    methods: list[Claim] = Field(default_factory=list)
    datasets: list[Claim] = Field(default_factory=list)
    results: list[Claim] = Field(default_factory=list)
    limitations: list[Claim] = Field(default_factory=list)


class Connection(Contract):
    connection_id: str
    kind: Literal["similarity", "difference", "conflict"]
    # For conflict, both sides must retain their own claim and evidence.
    claims: list[Claim] = Field(min_length=1)


class WriterRequest(Contract):
    task_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    topic: str = Field(min_length=1)
    papers: list[PaperDocument] = Field(min_length=1)
    reader_results: list[ReaderResult] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    common_references: ReferencesResult
    connections: list[Connection] = Field(default_factory=list)
    research_gaps: list[Claim] = Field(default_factory=list)
    output_format: Literal["markdown"] = "markdown"
    data_provenance: Literal["group2", "example_fixture"] = "group2"


class CoverageFeedback(Contract):
    missing_sections: list[Literal["introduction", "overview", "comparison", "common_references", "connections", "research_gaps", "limitations", "references"]] = Field(default_factory=list)
    missing_paper_ids: list[str] = Field(default_factory=list)
    note: str = ""


class RevisionRequest(Contract):
    report_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    feedback: CoverageFeedback
    updated_input: WriterRequest | None = None


class WriterResult(Contract):
    task_id: str
    report_id: str
    revision: int = Field(ge=0, le=1)
    status: Literal["needs_review", "coverage_incomplete"]
    markdown_path: str
    evidence_path: str
    markdown: str
    missing_coverage: list[str]
    warnings: list[str]
    mode: Literal["extractive", "groq"]
    evidence_verified: Literal[False] = False
    draft_path: str | None = None
    review_path: str | None = None
    decisions_path: str | None = None
    model_calls: int = Field(default=0,ge=0)
