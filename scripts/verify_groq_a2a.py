"""Explicit live test: local A2A Writer -> real Groq -> JSON/Markdown artifacts.

Uses the existing Writer mode/key configuration; never downgrades to extractive.
"""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from group3.common.analysis_schemas import WriterRequest, WriterResult
from group3.common.config import AnalysisSettings
from group3.agents.writer.validator import validate_input
from scripts.smoke_a2a import running, send


async def run(args):
    settings = AnalysisSettings()
    if settings.writer_mode != "groq":
        raise ValueError("Set GROUP3_WRITER_MODE=groq in .env before this live test")
    if not settings.groq_api_key or not settings.groq_api_key.get_secret_value().strip():
        raise ValueError("Set GROQ_API_KEY in .env before this live test")
    request = WriterRequest.model_validate_json(args.input.read_text(encoding="utf-8"))
    validate_input(request)
    with running("writer") as base:
        async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds + 30, trust_env=False) as client:
            card_response = await client.get(base + "/.well-known/agent-card.json")
            card_response.raise_for_status()
            card = card_response.json()
            assert card["protocolVersion"] == "0.3.0"
            task, data = await send(client, base, "write", request.model_dump(mode="json"))
            result = WriterResult.model_validate(data)
            assert result.mode == "groq" and result.model_calls>0 and not result.evidence_verified
            assert Path(result.markdown_path).read_text(encoding="utf-8") == result.markdown
            md_parts = [part["text"] for artifact in task["artifacts"] if artifact["name"] == "report.md" for part in artifact["parts"] if part["kind"] == "text"]
            assert md_parts == [result.markdown]
            queried = await client.post(base + "/",json={"jsonrpc":"2.0","id":uuid4().hex,
                "method":"tasks/get","params":{"id":task["id"]}})
            queried.raise_for_status()
            assert queried.json()["result"]["status"]["state"] == task["status"]["state"]
    record = {"tested_at":datetime.now(timezone.utc).isoformat(),
        "test_kind":"real_loopback_a2a_writer_with_actual_groq_api", "model":settings.groq_model,
        "input_data_provenance":request.data_provenance, "selected_count":len(request.papers),
        "actual_groq_api_called":True, "actual_group1_or_group2_service_called":False,
        "protocol_version":card["protocolVersion"], "a2a_task_id":task["id"],
        "a2a_state":task["status"]["state"], "tasks_get_verified":True,
        "markdown_artifact_matches_file":True, "result":result.model_dump(mode="json")}
    serialized = json.dumps(record,ensure_ascii=False,indent=2)
    # Fail closed rather than persist accidentally exposed credentials.
    assert settings.groq_api_key.get_secret_value() not in serialized
    args.result.parent.mkdir(parents=True,exist_ok=True)
    args.result.write_text(serialized,encoding="utf-8")
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.write_text(result.markdown,encoding="utf-8")
    print(f"Real A2A/Groq test passed: {result.mode}, {task['status']['state']}, {len(result.missing_coverage)} missing input fields")
    print(f"Report ID: {result.report_id}; record: {args.result}; Markdown: {args.markdown}")


def main():
    parser=argparse.ArgumentParser(description="Explicit live A2A/Groq integration test (API usage applies)")
    parser.add_argument("--input",type=Path,default=Path("examples/group2-example.json"))
    parser.add_argument("--result",type=Path,default=Path("docs/test-results/groq-a2a-live.json"))
    parser.add_argument("--markdown",type=Path,default=Path("examples/groq-a2a-report.md"))
    asyncio.run(run(parser.parse_args()))


if __name__=="__main__":
    main()
