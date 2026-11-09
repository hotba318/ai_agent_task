import hashlib
from pathlib import Path

from group3.agents.references.agent import CommonReferencesAgent
from group3.agents.retrieval.storage import JsonPaperStore
from group3.agents.writer.validator import missing_coverage, validate_input
from group3.common.analysis_schemas import WriterRequest
from .contracts import Group2Output


def verified_papers(root: Path, task_id: str, run_id: str):
    # StoreSelection validates names at the public boundary; revalidate for direct users.
    from group3.common.analysis_schemas import StoreSelection
    selection = StoreSelection(task_id=task_id, run_id=run_id)
    store = JsonPaperStore(root)
    folder = (store.root / selection.task_id / selection.run_id).resolve()
    if not folder.is_relative_to(store.root):
        raise ValueError("selected Paper Store escapes configured root")
    from group3.common.schemas import RetrievalResult
    manifest = RetrievalResult.model_validate_json((folder / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.task_id, manifest.run_id) != (selection.task_id, selection.run_id):
        raise ValueError("manifest task/run mismatch")
    papers = store.list_papers(folder)
    if [p.paper_id for p in papers] != manifest.paper_ids:
        raise ValueError("paper metadata IDs disagree with selected manifest")
    for paper in papers:
        for filename in (paper.raw_document_path, paper.parsed_document_path):
            path = Path(filename).resolve()
            if not path.is_relative_to(folder) or not path.is_file():
                raise ValueError("source file is missing or outside selected Paper Store")
        if hashlib.sha256(Path(paper.raw_document_path).read_bytes()).hexdigest() != paper.raw_sha256:
            raise ValueError(f"source SHA-256 mismatch: {paper.paper_id}")
    return papers


def assemble(group2: Group2Output, topic: str, store_root: Path):
    papers = verified_papers(store_root, group2.task_id, group2.run_id)
    if group2.paper_ids:
        if len(group2.paper_ids) != len(set(group2.paper_ids)):
            raise ValueError("duplicate Group 2 paper IDs")
        by_id = {p.paper_id: p for p in papers}
        if set(group2.paper_ids) - by_id.keys():
            raise ValueError("Group 2 paper not found in selected manifest")
        papers = [by_id[pid] for pid in group2.paper_ids]
    # Supplied Group 2 output cannot replace source papers or reference counts.
    refs = CommonReferencesAgent().analyze(papers, group2.task_id)
    request = WriterRequest(task_id=group2.task_id, topic=topic, papers=papers,
        reader_results=group2.reader_results, evidence=group2.evidence, common_references=refs,
        connections=group2.connections, research_gaps=group2.research_gaps,
        data_provenance=group2.data_provenance)
    validate_input(request)
    return request, missing_coverage(request)
