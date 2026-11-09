import os
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from group3.common.analysis_schemas import WriterRequest
from group3.common.config import AnalysisSettings
from group3.services import write_report


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_GROQ_LIVE") != "1", reason="opt in with RUN_GROQ_LIVE=1; calls paid external Groq API")
async def test_groq_real_report():
    settings = AnalysisSettings()
    if not settings.groq_api_key or not settings.groq_api_key.get_secret_value():
        pytest.skip("GROQ_API_KEY is not configured; no actual request was made")
    settings.writer_mode = "groq"
    settings.output_root = Path("data/groq-live-reports")
    request = WriterRequest.model_validate_json(Path("examples/writer-input.json").read_text(encoding="utf-8"))
    result = await write_report(request, settings)
    assert result.mode == "groq"
    assert result.model_calls>=2
    assert Path(result.markdown_path).exists()
    assert not result.evidence_verified
    output = Path("docs/test-results/groq-live-result.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"tested_at": datetime.now(timezone.utc).isoformat(),
        "test_kind": "actual_groq_api_with_example_group2_inputs", "model": settings.groq_model,
        "input_data_provenance": request.data_provenance, "actual_groq_api_called": True,
        "writer_implementation":"grounded_synthesis_with_support_review",
        "result": result.model_dump(mode="json")}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("examples/groq-report.md").write_text(result.markdown, encoding="utf-8")
