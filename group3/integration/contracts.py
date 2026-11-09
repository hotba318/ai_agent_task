import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from group3.common.analysis_schemas import (Claim, Connection, Evidence, ReaderResult,
    ReferencesRequest, ReferencesResult, RevisionRequest, StoreSelection, WriterRequest, WriterResult)
from group3.common.schemas import PaperDocument, RetrievalRequest, RetrievalResult


class Group2Output(StoreSelection):
    """Exchange envelope proposed for Group 2; not a finalized team contract."""
    reader_results: list[ReaderResult] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    research_gaps: list[Claim] = Field(default_factory=list)
    data_provenance: Literal["group2", "example_fixture"] = "group2"


MODELS = (RetrievalRequest, RetrievalResult, PaperDocument, ReferencesRequest, ReferencesResult,
          Group2Output, WriterRequest, RevisionRequest, WriterResult)


def export_schemas(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        schema = model.model_json_schema()
        schema["$comment"] = "Provisional Group 3 contract v0.1; requires agreement with Groups 1 and 2."
        (folder / (model.__name__ + ".schema.json")).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [model.__name__ + ".schema.json" for model in MODELS]
