from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GROUP3_", env_file=".env", extra="ignore")
    target_papers: int = Field(default=8, gt=0)
    minimum_papers: int = Field(default=7, gt=0)
    candidate_multiplier: int = Field(default=3, gt=0)
    download_delay_seconds: float = Field(default=15, ge=15)
    api_delay_seconds: float = Field(default=3, ge=3)
    store_root: Path = Path("data/papers")
    grobid_url: str = "http://localhost:8070"
    preferred_format: Literal["html", "pdf"] = "html"
    timeout_seconds: float = Field(default=60, gt=0)
    retries: int = Field(default=2, ge=0, le=5)
    freshness_field: Literal["submitted_date", "updated_date"] = "submitted_date"
    user_agent: str = "Group3PaperRetrieval/0.1"
    search_provider: Literal["auto", "arxiv", "datacite"] = "auto"
    max_search_rounds: int = Field(default=3,ge=1,le=5)
    retrieval_planner_mode: Literal["auto","rules","groq"] = "auto"

    @model_validator(mode="after")
    def counts(self):
        if self.minimum_papers > self.target_papers:
            raise ValueError("minimum_papers exceeds target_papers")
        return self


class AnalysisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GROUP3_", env_file=".env", extra="ignore")
    output_root: Path = Path("data/reports")
    writer_mode: Literal["extractive", "groq"] = "extractive"
    groq_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = "openai/gpt-oss-20b"
    groq_timeout_seconds: float = Field(default=90, gt=0)
    task_timeout_seconds: float = Field(default=600, gt=0)
