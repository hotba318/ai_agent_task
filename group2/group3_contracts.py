from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = "0.1"


class Section(Contract):
    section_id: str
    title: str
    text: str = Field(min_length=1)
    source_locator: str
    source_url: HttpUrl


class Reference(Contract):
    reference_id: str
    raw_text: str = Field(min_length=1)
    title: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1500, le=3000)
    source_locator: str


class PaperDocument(Contract):
    paper_id: str
    version_id: str
    title: str = Field(min_length=1)
    authors: list[str]
    abstract: str | None = None
    submitted_date: date
    updated_date: date
    source_url: HttpUrl
    html_url: HttpUrl
    pdf_url: HttpUrl
    metadata_source: Literal["arxiv_api", "datacite"] = "arxiv_api"
    metadata_url: HttpUrl | None = None
    parse_method: Literal["arxiv_html", "grobid_pdf"]
    raw_document_path: str
    parsed_document_path: str
    raw_sha256: str
    sections: list[Section] = Field(min_length=1)
    references: list[Reference]
    warnings: list[str] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    claims: list[Claim] = Field(min_length=1)


class ReaderAnalysis(Contract):
    reader_result: ReaderResult
    evidence: list[Evidence]


class ConnectionsRequest(Contract):
    reader_results: list[ReaderResult] = Field(min_length=2)
    evidence: list[Evidence] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence_references(self) -> "ConnectionsRequest":
        paper_ids = {result.paper_id for result in self.reader_results}
        if len(paper_ids) != len(self.reader_results):
            raise ValueError("reader_results must contain unique paper IDs.")
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        if len(evidence_by_id) != len(self.evidence):
            raise ValueError("evidence IDs must be unique.")
        if any(item.paper_id not in paper_ids for item in self.evidence):
            raise ValueError("Each evidence item must belong to a requested paper.")
        for result in self.reader_results:
            for claim in iter_claims(result):
                if not set(claim.evidence_ids) <= evidence_by_id.keys():
                    raise ValueError(f"Claim {claim.claim_id!r} has unknown evidence IDs.")
                if any(
                    evidence_by_id[evidence_id].paper_id != result.paper_id
                    for evidence_id in claim.evidence_ids
                ):
                    raise ValueError(
                        f"Claim {claim.claim_id!r} cites evidence from another paper."
                    )
        return self


class ConnectionsResult(Contract):
    connections: list[Connection]
    research_gaps: list[Claim] = Field(default_factory=list)


def iter_claims(result: ReaderResult) -> list[Claim]:
    return [
        claim
        for category in (
            result.overview,
            result.methods,
            result.datasets,
            result.results,
            result.limitations,
        )
        for claim in category
    ]
