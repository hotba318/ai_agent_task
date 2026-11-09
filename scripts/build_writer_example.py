"""Build an explicitly labelled sparse example from actually retrieved source excerpts.

No invented analysis or benchmark metrics. Missing Group 2 outputs remain missing.
"""
import argparse
import re
from pathlib import Path

from group3.agents.references.agent import CommonReferencesAgent
from group3.agents.retrieval.storage import JsonPaperStore
from group3.common.analysis_schemas import Claim, Evidence, ReaderResult, WriterRequest


def build(folder: Path, task_id: str):
    papers = JsonPaperStore(folder.parent.parent).list_papers(folder)
    readers, evidence = [], []
    for index, paper in enumerate(papers):
        fields = {}
        for name, pattern in (("overview", None), ("methods", r"method|approach|framework|architecture"),
                              ("results", r"result|evaluation|experiment"), ("limitations", r"limitation")):
            section = paper.sections[0] if pattern is None else next((s for s in paper.sections if re.search(pattern, s.title, re.I)), None)
            if section is None:
                continue
            quote = section.text[:500]
            eid = f"example-{index}-{name}"
            evidence.append(Evidence(evidence_id=eid, paper_id=paper.paper_id, section_id=section.section_id, quote=quote))
            fields[name] = [Claim(claim_id=f"claim-{eid}", text="예시: 해당 섹션의 원문 발췌 — " + quote, evidence_ids=[eid])]
        readers.append(ReaderResult(paper_id=paper.paper_id, **fields))
    return WriterRequest(task_id=task_id, topic="Multi-agent large language models", papers=papers,
        reader_results=readers, evidence=evidence, common_references=CommonReferencesAgent().analyze(papers, task_id),
        data_provenance="example_fixture")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-folder", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", type=Path, default=Path("examples/writer-input.json"))
    args = parser.parse_args()
    request = build(args.store_folder, args.task_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    print(f"Example written: {args.output}; {len(request.papers)} real papers, {len(request.evidence)} source excerpts; no inferred datasets/gaps/connections")


if __name__ == "__main__":
    main()
