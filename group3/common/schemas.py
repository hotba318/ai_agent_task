"""Provisional local contracts. A2A and Group 2 mapping remain unagreed."""
import re
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["0.1"] = "0.1"


class RetrievalRequest(Contract):
    task_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    topic: str = Field(min_length=1)
    target_papers: int = Field(default=8, gt=0)
    minimum_papers: int = Field(default=7, gt=0)

    @field_validator("topic")
    @classmethod
    def topic_not_blank(cls, value):
        if not value.strip():
            raise ValueError("topic cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def counts(self):
        if self.minimum_papers > self.target_papers:
            raise ValueError("minimum_papers exceeds target_papers")
        return self


def canonical_arxiv_id(value: str) -> str:
    value = re.sub(r"^.*(?:/abs/|/pdf/)", "", value.removeprefix("arxiv:"))
    value = re.sub(r"\.pdf$", "", value)
    value = re.sub(r"v\d+$", "", value)
    if not re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7})", value):
        raise ValueError("invalid arXiv id")
    return "arxiv:" + value


class PaperMetadata(Contract):
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

    @field_validator("paper_id")
    @classmethod
    def normalize_id(cls, value):
        return canonical_arxiv_id(value)


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


class PaperDocument(PaperMetadata):
    parse_method: Literal["arxiv_html", "grobid_pdf"]
    raw_document_path: str
    parsed_document_path: str
    raw_sha256: str
    sections: list[Section] = Field(min_length=1)
    references: list[Reference]
    warnings: list[str] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Failure(Contract):
    paper_id: str | None = None
    stage: str
    code: str
    detail: str


class RetrievalResult(Contract):
    task_id: str
    run_id: str
    status: Literal["completed", "insufficient_papers", "failed"]
    requested_count: int
    selected_count: int
    paper_store_uri: str
    paper_ids: list[str]
    warnings: list[str] = Field(default_factory=list)
    failures: list[Failure] = Field(default_factory=list)
    decisions_path: str | None = None

    @model_validator(mode="after")
    def selected_ids_match(self):
        if self.selected_count != len(set(self.paper_ids)) or self.selected_count != len(self.paper_ids):
            raise ValueError("selected_count must equal unique paper_ids")
        return self
