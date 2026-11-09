"""Conservative bibliographic matching; never invent missing metadata."""
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import unquote

from group3.common.analysis_schemas import ReferenceOccurrence
from group3.common.schemas import Reference, canonical_arxiv_id


def normalized_text(value: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold()))


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = unquote(value.strip()).casefold()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
    value = value.rstrip(".,;")
    # Do not strip balanced DOI parentheses (valid identifiers).
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value if re.fullmatch(r"10\.\d{4,9}/\S+", value) else None


def normalize_arxiv(value: str | None) -> str | None:
    if value:
        try:
            return canonical_arxiv_id(value.strip().removeprefix("arXiv:")).casefold()
        except ValueError:
            pass
    return None


@dataclass
class Item:
    ref: Reference
    occurrence: ReferenceOccurrence
    doi: str | None
    arxiv: str | None
    title: str
    fingerprint: str

    @property
    def ids(self):
        return {k: {v} for k, v in (("doi", self.doi), ("arxiv", self.arxiv)) if v}


def item(paper_id: str, ref: Reference) -> Item:
    # Raw fallback is intentionally exact after removing per-paper citation back-links.
    raw = re.split(r"\bCited by\s*:", ref.raw_text, flags=re.I)[0]
    raw = re.sub(r"^\s*\[\d+\]\s*", "", raw)
    doi = normalize_doi(ref.doi)
    arxiv = normalize_arxiv(ref.arxiv_id)
    return Item(ref, ReferenceOccurrence(paper_id=paper_id, reference_id=ref.reference_id,
        source_locator=ref.source_locator, raw_text=ref.raw_text), doi, arxiv,
        normalized_text(ref.title or ""), normalized_text(raw))


def same_metadata(a: Item, b: Item) -> bool:
    return bool(a.title and a.title == b.title and a.ref.year and a.ref.year == b.ref.year
        and a.ref.authors and b.ref.authors
        and sorted(normalized_text(v) for v in a.ref.authors) == sorted(normalized_text(v) for v in b.ref.authors))


def stable_local_id(value: str) -> str:
    return "local:" + hashlib.sha256(value.encode()).hexdigest()[:24]


def match(items: list[Item]):
    """Union strong IDs first; conflicting namespaces never coalesce transitively."""
    parents = list(range(len(items)))
    identifiers = [entry.ids for entry in items]
    ambiguous = []

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    pairs = []
    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            b = items[j]
            strong = bool((a.doi and a.doi == b.doi) or (a.arxiv and a.arxiv == b.arxiv))
            exact = same_metadata(a, b)
            raw_equal = bool(len(a.fingerprint) >= 40 and a.fingerprint == b.fingerprint)
            if strong or exact or raw_equal:
                pairs.append((0 if strong else 1, i, j))
            elif a.title and b.title and SequenceMatcher(None, a.title, b.title).ratio() >= .9:
                ambiguous.append((i, j, "similar_title_without_sufficient_identity"))
    for _, i, j in sorted(pairs):
        ri, rj = root(i), root(j)
        if ri == rj:
            continue
        combined = {key: identifiers[ri].get(key, set()) | identifiers[rj].get(key, set()) for key in ("doi", "arxiv")}
        if any(len(values) > 1 for values in combined.values()):
            ambiguous.append((i, j, "conflicting_identifiers"))
            continue
        parents[rj] = ri
        identifiers[ri] = combined
    groups = {}
    for i, entry in enumerate(items):
        groups.setdefault(root(i), []).append(entry)
    return list(groups.values()), [(items[i].occurrence, items[j].occurrence, reason)
        for i, j, reason in ambiguous if root(i) != root(j)]
