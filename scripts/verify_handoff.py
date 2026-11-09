"""Local handoff proof: real stored sources, relocated store, example Group 2, SDK HTTP.

Does not contact Groq/arXiv, and does not impersonate actual Group 1/2 services.
"""
import argparse
import asyncio
import json
import os
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

import httpx

from group3.common.analysis_schemas import StoreSelection
from group3.common.config import Settings
from group3.integration.assembler import assemble, verified_papers
from group3.integration.bundle import export_bundle, import_bundle
from group3.integration.contracts import Group2Output, export_schemas
from scripts.build_group2_example import build
from scripts.smoke_a2a import running, send


async def run(args):
    source_root=Settings().store_root
    output=Path("data/handoff-runs")/uuid4().hex
    output.mkdir(parents=True)
    selection=StoreSelection(task_id=args.task_id,run_id=args.run_id)
    archive=output/"paper-store.zip"
    index=export_bundle(source_root,selection,archive)
    imported=import_bundle(archive,output/"relocated-store")
    papers=verified_papers(output/"relocated-store",selection.task_id,selection.run_id)
    assert len(papers)==len(index.papers)
    imported_folder=(output/"relocated-store"/selection.task_id/selection.run_id).resolve()
    example=build(imported_folder,selection.task_id)
    group2=Group2Output(task_id=selection.task_id,run_id=selection.run_id,
        reader_results=example.reader_results,evidence=example.evidence,connections=example.connections,
        research_gaps=example.research_gaps,data_provenance="example_fixture")
    request,missing=assemble(group2,example.topic,output/"relocated-store")
    example_path=args.example_output
    example_path.parent.mkdir(parents=True,exist_ok=True)
    example_path.write_text(group2.model_dump_json(indent=2),encoding="utf-8")
    (output/"writer-input.json").write_text(request.model_dump_json(indent=2),encoding="utf-8")
    export_schemas(Path("docs/contracts"))
    previous={key:os.environ.get(key) for key in ("GROUP3_STORE_ROOT","GROUP3_OUTPUT_ROOT","GROUP3_WRITER_MODE")}
    os.environ.update({"GROUP3_STORE_ROOT":str((output/"relocated-store").resolve()),
        "GROUP3_OUTPUT_ROOT":str((output/"reports").resolve()),"GROUP3_WRITER_MODE":"extractive"})
    try:
        with ExitStack() as stack:
            refs_url=stack.enter_context(running("references"))
            writer_url=stack.enter_context(running("writer"))
            async with httpx.AsyncClient(timeout=60) as client:
                refs_task,refs=await send(client,refs_url,"references",selection.model_dump(mode="json"))
                assert refs==request.common_references.model_dump(mode="json")
                task,result=await send(client,writer_url,"write",request.model_dump(mode="json"))
                assert result["evidence_verified"] is False
                assert result["missing_coverage"]==missing
    finally:
        for key,value in previous.items():
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key]=value
    record={"test_kind":"local_portable_store_roundtrip_and_real_loopback_a2a", "paper_count":len(papers),
        "source_task":selection.model_dump(),"bundle_path":str(archive.resolve()),
        "imported_manifest":imported.model_dump(mode="json"),"common_reference_count":len(refs["common_references"]),
        "references_a2a_state":refs_task["status"]["state"],"writer_a2a_state":task["status"]["state"],
        "writer_result":result,"group2_provenance":"example_fixture","groq_api_called":False,
        "arxiv_api_called":False,"actual_other_group_services_called":False}
    args.result.parent.mkdir(parents=True,exist_ok=True)
    args.result.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Handoff success: {len(papers)} source papers relocated; {len(refs['common_references'])} common references; Writer {result['status']}")
    print(f"Archive: {archive}; record: {args.result}")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--task-id",required=True)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--result",type=Path,default=Path("docs/test-results/handoff-loopback.json"))
    parser.add_argument("--example-output",type=Path,default=Path("examples/group2-output.example.json"))
    asyncio.run(run(parser.parse_args()))


if __name__=="__main__":
    main()
