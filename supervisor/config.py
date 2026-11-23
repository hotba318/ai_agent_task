from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SupervisorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUPERVISOR_", env_file=".env", extra="ignore")

    # Where each agent service listens (A2A base addresses)
    service_url: str = "http://127.0.0.1:9100"
    retrieval_url: str = "http://127.0.0.1:9101"
    reader_url: str = "http://127.0.0.1:9102"
    references_url: str = "http://127.0.0.1:9103"
    connections_url: str = "http://127.0.0.1:9104"
    writer_url: str = "http://127.0.0.1:9105"
    agent_timeout_seconds: float = Field(default=600, gt=0)

    # How a run behaves (team decisions)
    target_papers: int = Field(default=5, gt=0)
    minimum_papers: int = Field(default=4, gt=0)
    min_citing_papers: int = Field(default=2, ge=2)
    coverage_retries: int = Field(default=1, ge=0)
    evidence_retries: int = Field(default=2, ge=0)

    # The supervisor's own LLM and memory
    groq_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = Field(default=90, gt=0)
    memory_path: Path = Path("data/supervisor/memory.db")
    reports_path: Path = Path("data/supervisor/reports")
