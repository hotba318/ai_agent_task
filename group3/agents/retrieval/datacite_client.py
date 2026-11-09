"""Independent public DOI metadata search, restricted to registered arXiv records."""
import re
from datetime import datetime
from urllib.parse import urlparse

from group3.common.schemas import PaperMetadata, canonical_arxiv_id


def parse_arxiv_record(record):
    a = record["attributes"]
    doi = a["doi"].lower()
    if not doi.startswith("10.48550/arxiv."):
        raise ValueError("not an arXiv DOI")
    paper_id = canonical_arxiv_id(doi.removeprefix("10.48550/arxiv."))
    publisher = a.get("publisher", "")
    publisher = publisher.get("name", "") if isinstance(publisher, dict) else publisher
    if publisher.casefold() != "arxiv":
        raise ValueError("record publisher is not arXiv")
    link = urlparse(a["url"])
    if link.hostname not in {"arxiv.org", "www.arxiv.org"} or not link.path.startswith("/abs/") or canonical_arxiv_id(link.path.removeprefix("/abs/")) != paper_id:
        raise ValueError("DOI and arXiv landing page disagree")
    # DataCite created/registered dates are NOT arXiv submission dates.
    # Require explicitly versioned Submitted dates, including the initial version.
    submitted = {}
    for date in a.get("dates", []):
        if date.get("dateType") == "Submitted" and re.fullmatch(r"v[1-9]\d*", date.get("dateInformation", "")):
            ver = int(date["dateInformation"][1:])
            parsed = datetime.fromisoformat(date["date"].replace("Z", "+00:00")).date()
            if ver in submitted and submitted[ver] != parsed:
                raise ValueError("conflicting submission dates")
            submitted[ver] = parsed
    version = str(a.get("version", ""))
    if not version.isdigit() or int(version) < 1 or 1 not in submitted or int(version) not in submitted:
        raise ValueError("missing verified initial/current submission date or version")
    if int(version) != max(submitted) or submitted[1] > submitted[int(version)]:
        raise ValueError("inconsistent arXiv version chronology")
    version_id = paper_id.removeprefix("arxiv:") + "v" + version
    abstract = next((d["description"] for d in a.get("descriptions", []) if d.get("descriptionType") == "Abstract" and d.get("description", "").strip()), None)
    return PaperMetadata(paper_id=paper_id, version_id=version_id, title=a["titles"][0]["title"].strip(),
        authors=[c["name"].strip() for c in a.get("creators", []) if c.get("name", "").strip()], abstract=abstract,
        submitted_date=submitted[1], updated_date=submitted[int(version)],
        source_url=f"https://arxiv.org/abs/{version_id}", html_url=f"https://arxiv.org/html/{version_id}",
        pdf_url=f"https://arxiv.org/pdf/{version_id}", metadata_source="datacite",
        metadata_url=f"https://api.datacite.org/dois/{doi}")


class DataCiteClient:
    error_source = "datacite"
    def __init__(self, transport):
        self.transport = transport
        self.warnings = []

    async def search(self, topic, limit):
        self.warnings = []
        tokens = re.findall(r"[^\W_]+", topic, re.UNICODE)
        if not tokens:
            raise ValueError("topic has no searchable terms")
        response = await self.transport.request("GET", "https://api.datacite.org/dois", params={
            "query": " AND ".join(f'"{token}"' for token in tokens),
            "prefix": "10.48550", "page[size]": limit, "sort": "relevance"})
        records = response.json()["data"]
        papers = []
        for record in records:
            try:
                papers.append(parse_arxiv_record(record))
            except (KeyError, ValueError, TypeError, IndexError):
                self.warnings.append("Skipped a DataCite record with incomplete/inconsistent arXiv identity, version, or submission metadata.")
        return papers
