import re

from group3.common.schemas import PaperMetadata

STOP = {"a", "an", "the", "for", "of", "in", "on", "and", "to", "with", "using"}


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP


class KeywordRanker:
    """Documented provisional relevance bands, then freshness. No citation-count bias."""

    def __init__(self, freshness_field="submitted_date"):
        self.freshness_field = freshness_field

    def rank(self, topic: str, papers: list[PaperMetadata]) -> list[PaperMetadata]:
        query = tokens(topic)
        if not query:
            raise ValueError("keyword ranker requires English searchable topic terms")
        scored = {}
        for paper in papers:
            coverage = len(query & tokens(paper.title + " " + (paper.abstract or ""))) / len(query)
            band = 2 if coverage >= .75 else 1 if coverage >= .5 else 0
            if not band:
                continue
            previous = scored.get(paper.paper_id)
            if previous is None or paper.updated_date > previous[1].updated_date:
                scored[paper.paper_id] = (band, paper)
        ordered = sorted(scored.values(), key=lambda item: (
            -item[0], -getattr(item[1], self.freshness_field).toordinal(), item[1].paper_id,
        ))
        return [paper for _, paper in ordered]
