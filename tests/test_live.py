import os
from pathlib import Path

import pytest

from group3.cli import retrieve
from group3.common.config import Settings
from group3.common.schemas import RetrievalRequest
from group3.agents.retrieval.storage import JsonPaperStore


@pytest.mark.live
@pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="opt in with RUN_LIVE=1; downloads real papers")
async def test_three_real_papers():
    settings = Settings()
    request = RetrievalRequest(task_id="live-smoke", topic="multi agent large language models", target_papers=3, minimum_papers=3)
    result = await retrieve(request, settings)
    output = Path("docs/test-results/live-result.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    assert result.status == "completed", result.model_dump_json()
    folder = settings.store_root.resolve() / result.task_id / result.run_id
    documents = JsonPaperStore(settings.store_root).list_papers(folder)
    assert len(documents) == 3
    for doc in documents:
        assert Path(doc.raw_document_path).exists()
        assert doc.sections
        assert doc.references, "live smoke requires extracted references, not invented placeholders"
