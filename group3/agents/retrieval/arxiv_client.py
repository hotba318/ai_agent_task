import re
from datetime import datetime

from lxml import etree

from group3.common.schemas import PaperMetadata
from .downloader import HttpTransport

ATOM = {"a": "http://www.w3.org/2005/Atom"}


def parse_feed(content: bytes) -> list[PaperMetadata]:
    root = etree.fromstring(content, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    papers = []
    for entry in root.findall("a:entry", ATOM):
        def value(name):
            return " ".join((entry.findtext("a:" + name, namespaces=ATOM) or "").split())
        identifier = value("id")
        if "arxiv.org/api/errors" in identifier:
            raise ValueError("arXiv API error: " + value("summary"))
        version = identifier.split("/abs/")[-1]
        papers.append(PaperMetadata(
            paper_id=version, version_id=version, title=value("title"),
            abstract=value("summary") or None,
            authors=[" ".join(a.itertext()).strip() for a in entry.findall("a:author/a:name", ATOM)],
            submitted_date=datetime.fromisoformat(value("published").replace("Z", "+00:00")).date(),
            updated_date=datetime.fromisoformat(value("updated").replace("Z", "+00:00")).date(),
            source_url=f"https://arxiv.org/abs/{version}",
            html_url=f"https://arxiv.org/html/{version}", pdf_url=f"https://arxiv.org/pdf/{version}",
        ))
    return papers


class ArxivClient:
    def __init__(self, transport: HttpTransport):
        self.transport = transport

    async def search(self, topic: str, limit: int) -> list[PaperMetadata]:
        # Quote tokens, rather than interpreting user text as arXiv query operators.
        terms = re.findall(r"[^\W_]+", topic, re.UNICODE)
        if not terms:
            raise ValueError("topic has no searchable terms")
        response = await self.transport.request("GET", "https://export.arxiv.org/api/query", params={
            "search_query": " AND ".join(f'all:"{term}"' for term in terms),
            "start": 0, "max_results": limit, "sortBy": "relevance", "sortOrder": "descending",
        })
        return parse_feed(response.content)
