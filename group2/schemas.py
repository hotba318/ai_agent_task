from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def gemini_response_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()

    def remove_unsupported_fields(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned = {
                key: remove_unsupported_fields(item)
                for key, item in value.items()
                if key not in {"additionalProperties", "const"}
            }
            if "const" in value:
                cleaned["enum"] = [value["const"]]
            return cleaned
        if isinstance(value, list):
            return [remove_unsupported_fields(item) for item in value]
        return value

    return remove_unsupported_fields(schema)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimEvidence(StrictModel):
    claim: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    section: str = Field(min_length=1)


class PaperTemplate(StrictModel):
    paper_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    core_problem: str
    proposed_method: str
    datasets: list[str]
    key_findings: list[str]
    limitations: list[str]


class ExtractRequest(StrictModel):
    paper_id: str = Field(min_length=1)
    title: str = ""
    sections: list[str] = Field(default_factory=list)


class PaperStoreEntry(StrictModel):
    title: str = Field(min_length=1)
    sections: list[str] = Field(min_length=1)


class ClaimVerificationRequest(StrictModel):
    paper_id: str = Field(min_length=1)
    evidence: ClaimEvidence
    paper_text: str = ""


class ClaimVerificationResult(StrictModel):
    verified: bool
    corrected_claim: str
    notes: str


class TaskState(StrictModel):
    task_id: str
    paper_id: str
    status: str
    retry_count: int
    notes: str


class SupervisorReviewResult(StrictModel):
    paper: PaperTemplate
    verifications: list[ClaimVerificationResult]
    status: str
    retry_count: int


class PaperRelation(StrictModel):
    paper_ids: list[str] = Field(min_length=2)
    relation_type: Literal[
        "shared_method",
        "shared_dataset",
        "consistent_finding",
        "conflicting_finding",
        "other_connection",
    ]
    description: str
    supporting_details: list[str] = Field(default_factory=list)


class ConnectionsRequest(StrictModel):
    papers: list[PaperTemplate] = Field(min_length=2)

    @model_validator(mode="after")
    def paper_ids_are_unique(self) -> "ConnectionsRequest":
        paper_ids = [paper.paper_id for paper in self.papers]
        if len(set(paper_ids)) != len(paper_ids):
            raise ValueError("Each paper must have a unique paper_id.")
        return self


class ConnectionsReport(StrictModel):
    relations: list[PaperRelation]
    cross_paper_synthesis: str
    research_gaps: list[str]
