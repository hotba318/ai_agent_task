from .downloader import HttpRequestError


class ResilientSearch:
    """One arXiv attempt followed by independent metadata service on availability errors."""
    def __init__(self, arxiv, datacite):
        self.arxiv, self.datacite = arxiv, datacite
        self.warnings = []
        self.error_source = "arxiv"
        self.primary_unavailable = None

    async def search(self, topic, limit):
        self.warnings = []
        self.error_source = "arxiv"
        if self.primary_unavailable is None:
            try:
                return await self.arxiv.search(topic, limit)
            except HttpRequestError as exc:
                if exc.status_code != 429 and not (exc.status_code and exc.status_code >= 500) and exc.code not in {"network_error", "timeout"}:
                    raise
                self.primary_unavailable=f"{exc.code}, HTTP {exc.status_code}"
        self.warnings.append(f"arXiv API unavailable ({self.primary_unavailable}); searched live DataCite arXiv DOI records instead. This is not arXiv API recovery or a cached search.")
        self.error_source = "datacite"
        papers = await self.datacite.search(topic, limit)
        self.warnings.extend(self.datacite.warnings)
        return papers
