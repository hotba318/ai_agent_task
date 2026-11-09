"""One-paper, explicitly targeted real PDF/GROBID verification. No demo URL fallback."""
import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from group3.agents.retrieval.downloader import HttpTransport, RequestGate
from group3.agents.retrieval.fetcher import DocumentPipeline
from group3.agents.retrieval.storage import JsonPaperStore
from group3.common.analysis_schemas import StoreSelection
from group3.common.config import Settings
from group3.common.schemas import Failure, PaperMetadata, RetrievalResult, canonical_arxiv_id
from .assembler import verified_papers


async def verify_grobid(settings, selection, paper_id, grobid_url, *, client=None):
    originals = verified_papers(settings.store_root, selection.task_id, selection.run_id)
    paper_id = canonical_arxiv_id(paper_id)
    original = next((p for p in originals if p.paper_id == paper_id), None)
    if original is None:
        raise ValueError("paper_id is not in the selected source store")
    endpoint = httpx.URL(grobid_url)
    if endpoint.scheme not in {"http", "https"} or not endpoint.host or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ValueError("GROBID probe requires a plain HTTP(S) service URL")
    if client is None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=20), follow_redirects=True,
            limits=httpx.Limits(max_connections=1), headers={"User-Agent": settings.user_agent}) as http:
            return await _probe(http, settings, selection, original, grobid_url)
    return await _probe(client, settings, selection, original, grobid_url)


async def _probe(client, settings, selection, original, grobid_url):
    task_id, run_id = "grobid-pdf-smoke", uuid4().hex
    store = JsonPaperStore(settings.store_root)
    folder = store.begin(task_id, run_id)
    record = {"schema_version": "0.1", "tested_at": datetime.now(timezone.utc).isoformat(),
        "test_kind": "explicit_pdf_preference_grobid_integration", "success": False,
        "source_selection": selection.model_dump(), "paper_id": original.paper_id,
        "pdf_url": str(original.pdf_url), "grobid_host": httpx.URL(grobid_url).host,
        "grobid_version": None, "post_attempts": 0, "parse_method": None,
        "paper_store_uri": folder.as_uri(), "source_store_modified": False,
        "html_reference_count": len(original.references), "fact_verification_performed": False}
    ids, failures, warnings = [], [], []
    try:
        alive = await client.get(grobid_url.rstrip("/") + "/api/isalive")
        if alive.status_code != 200 or alive.text.strip().lower() != "true":
            raise RuntimeError("GROBID liveness check did not pass")
        version = await client.get(grobid_url.rstrip("/") + "/api/version")
        if version.status_code == 200:
            try:
                value = version.json()
                record["grobid_version"] = str(value.get("version", "unknown")) if isinstance(value, dict) else None
            except ValueError:
                pass
        downloads = HttpTransport(client, RequestGate(settings.download_delay_seconds), retries=0)
        class CountingTransport(HttpTransport):
            async def request(self, method, url, **kwargs):
                if method == "POST":
                    record["post_attempts"] += 1
                return await super().request(method, url, **kwargs)
        grobid = CountingTransport(client, RequestGate(0), retries=0)
        metadata = PaperMetadata.model_validate({key: getattr(original, key) for key in PaperMetadata.model_fields})
        document = await DocumentPipeline(downloads, grobid, grobid_url, preferred_format="pdf").fetch(metadata, folder)
        store.save(folder, document)
        ids.append(document.paper_id)
        record.update({"parse_method": document.parse_method, "sections": len(document.sections),
            "references": len(document.references), "raw_document_path": document.raw_document_path,
            "tei_path": document.parsed_document_path if document.parse_method == "grobid_pdf" else None,
            "raw_sha256_verified": hashlib.sha256(Path(document.raw_document_path).read_bytes()).hexdigest() == document.raw_sha256,
            "references_with_title": sum(bool(r.title) for r in document.references)})
        warnings.extend(document.warnings)
        record["success"] = document.parse_method == "grobid_pdf" and bool(document.sections) and bool(document.references) and record["raw_sha256_verified"]
        if document.parse_method != "grobid_pdf":
            warnings.append("PDF/GROBID did not succeed; HTML fallback is not a successful PDF probe.")
    except Exception as exc:
        # Persist the failed attempt without claiming parsing succeeded or dumping upstream bodies.
        failures.append(Failure(paper_id=original.paper_id, stage="grobid_live_probe", code=type(exc).__name__, detail="Real PDF/GROBID verification did not complete; inspect raw artifacts and service configuration."))
        record["error_type"] = type(exc).__name__
    result = RetrievalResult(task_id=task_id, run_id=run_id, status="completed" if record["success"] else "failed",
        requested_count=1, selected_count=len(ids), paper_store_uri=folder.as_uri(), paper_ids=ids, warnings=warnings, failures=failures)
    store.finish(folder, result)
    record["retrieval"] = result.model_dump(mode="json")
    (folder / "probe.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description="Verify one public PDF against an explicitly selected GROBID endpoint")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--grobid-url", required=True)
    parser.add_argument("--result", type=Path, default=Path("docs/test-results/grobid-live.json"))
    args = parser.parse_args()
    record = asyncio.run(verify_grobid(Settings(), StoreSelection(task_id=args.task_id,run_id=args.run_id),args.paper_id,args.grobid_url))
    args.result.parent.mkdir(parents=True,exist_ok=True)
    args.result.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False,indent=2))
    return 0 if record["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
