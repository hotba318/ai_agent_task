from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname
from group3.agents.retrieval.storage import JsonPaperStore
from group3.common.schemas import PaperDocument, RetrievalResult


def load_papers(retrieval: RetrievalResult) -> list[PaperDocument]:
    """The full papers behind a retrieval result, read from the paper store the retrieval agent wrote."""
    uri = urlparse(retrieval.paper_store_uri)
    if uri.scheme != 'file':
        raise ValueError(f'unsupported paper store: {retrieval.paper_store_uri}')
    folder = Path(url2pathname(uri.path))
    return JsonPaperStore(folder).list_papers(folder)