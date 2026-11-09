import hashlib
from pathlib import Path
from typing import Literal

from group3.common.schemas import Failure, PaperDocument, PaperMetadata
from .downloader import HttpTransport
from .parser import parse_html, parse_tei
from .storage import JsonPaperStore


class FetchError(Exception):
    def __init__(self, failures):
        self.failures = failures
        super().__init__("all document formats failed")


class DocumentPipeline:
    def __init__(self, downloads: HttpTransport, grobid: HttpTransport, grobid_url: str,
                 preferred_format: Literal["html", "pdf"] = "html"):
        if preferred_format not in {"html", "pdf"}:
            raise ValueError("preferred_format must be html or pdf")
        self.downloads, self.grobid, self.grobid_url = downloads, grobid, grobid_url.rstrip("/")
        self.preferred_format = preferred_format

    async def fetch(self, paper: PaperMetadata, folder: Path) -> PaperDocument:
        key = JsonPaperStore.key(paper.paper_id)
        failures = []
        formats = ("html", "pdf") if self.preferred_format == "html" else ("pdf", "html")
        for format_name in formats:
            try:
                if format_name == "html":
                    response = await self.downloads.request("GET", str(paper.html_url))
                    raw = response.content
                    raw_path = folder / (key + ".html")
                    raw_path.write_bytes(raw)
                    sections, references = parse_html(raw, str(paper.html_url))
                    parsed_path, method = raw_path, "arxiv_html"
                else:
                    response = await self.downloads.request("GET", str(paper.pdf_url))
                    raw = response.content
                    if not raw.startswith(b"%PDF-"):
                        raise ValueError("download is not a PDF")
                    raw_path = folder / (key + ".pdf")
                    raw_path.write_bytes(raw)
                    response = await self.grobid.request("POST", self.grobid_url + "/api/processFulltextDocument",
                        files={"input": (raw_path.name, raw, "application/pdf")},
                        data={"includeRawCitations": "1", "consolidateCitations": "0", "consolidateHeader": "0"})
                    parsed_path = folder / (key + ".tei.xml")
                    parsed_path.write_bytes(response.content)
                    sections, references = parse_tei(response.content, str(paper.pdf_url))
                    method = "grobid_pdf"
                break
            except Exception as exc:
                stage = "html" if format_name == "html" else "pdf_grobid"
                failures.append(Failure(paper_id=paper.paper_id, stage=stage, code=type(exc).__name__, detail=str(exc)))
        else:
            raise FetchError(failures)
        warnings = [f"{f.stage}: {f.code}: {f.detail}" for f in failures]
        if not references:
            warnings.append("No references extracted; absence of citations is not established.")
        return PaperDocument(**paper.model_dump(exclude={"schema_version"}), parse_method=method,
            raw_document_path=str(raw_path.resolve()), parsed_document_path=str(parsed_path.resolve()),
            raw_sha256=hashlib.sha256(raw).hexdigest(), sections=sections, references=references, warnings=warnings)
