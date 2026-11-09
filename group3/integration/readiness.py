from pathlib import Path

import httpx
from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from group3.common.config import AnalysisSettings, Settings
from .assembler import assemble, verified_papers
from .contracts import Group2Output


class IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GROUP3_", env_file=".env", extra="ignore")
    supervisor_url: HttpUrl | None = None
    reader_url: HttpUrl | None = None
    connections_url: HttpUrl | None = None


async def check_readiness(settings: Settings, analysis: AnalysisSettings, integration: IntegrationSettings,
                          *, selection=None, group2_input: Path | None = None, client=None):
    checks = []
    def add(name, status, code):
        checks.append({"name": name, "status": status, "code": code})
    present = bool(analysis.groq_api_key and analysis.groq_api_key.get_secret_value().strip())
    add("groq", "configured_unverified" if present else "missing", "key_present_no_api_call" if present else "api_key_missing")
    if client is None:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as local_client:
            await _grobid(local_client, settings.grobid_url, add)
    else:
        await _grobid(client, settings.grobid_url, add)
    for name in ("supervisor", "reader", "connections"):
        configured = getattr(integration, name + "_url") is not None
        add(name, "configured_unverified" if configured else "missing", "endpoint_configured_contract_unverified" if configured else "endpoint_missing")
    if selection:
        try:
            papers = verified_papers(settings.store_root, selection.task_id, selection.run_id)
            add("paper_store", "passed", f"verified_{len(papers)}_paper_files")
        except (OSError, ValueError):
            add("paper_store", "failed", "store_validation_failed")
    else:
        add("paper_store", "missing", "selection_not_provided")
    if group2_input:
        try:
            output = Group2Output.model_validate_json(group2_input.read_text(encoding="utf-8"))
            request, missing = assemble(output, "Integration input validation", settings.store_root)
            add("group2_input", "configured_unverified" if output.data_provenance == "example_fixture" else "passed",
                "example_fixture_only" if output.data_provenance == "example_fixture" else "declared_group2_input_structurally_valid")
            if missing:
                add("coverage", "failed", f"missing_{len(missing)}_input_fields")
            else:
                add("coverage", "passed", "required_input_fields_present")
        except (OSError, ValueError):
            add("group2_input", "failed", "group2_input_validation_failed")
    else:
        add("group2_input", "missing", "actual_group2_output_not_provided")
    example_only = any(c["code"] == "example_fixture_only" for c in checks)
    return {"schema_version": "0.1", "all_checks_verified": all(c["status"] == "passed" for c in checks),
            "ready_for_external_attempt": not example_only and all(c["status"] in {"passed", "configured_unverified"} for c in checks),
            "checks": checks, "groq_api_called": False, "fact_verification_performed": False}


async def _grobid(client, base_url, add):
    try:
        response = await client.get(base_url.rstrip("/") + "/api/isalive")
        alive = response.status_code == 200 and response.text.strip().casefold() == "true"
        add("grobid", "passed" if alive else "failed", "liveness_passed_parsing_unverified" if alive else "not_alive")
    except httpx.HTTPError:
        # No exception body or URL is emitted; it could contain credentials.
        add("grobid", "failed", "unreachable")
