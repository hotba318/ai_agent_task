import hashlib
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from group3.agents.retrieval.storage import JsonPaperStore
from group3.common.analysis_schemas import Claim, Evidence, ReaderResult, StoreSelection
from group3.common.config import AnalysisSettings, Settings
from group3.common.schemas import RetrievalResult
from group3.integration.assembler import assemble, verified_papers
from group3.integration.bundle import export_bundle, import_bundle, inspect_bundle
from group3.integration.contracts import Group2Output, export_schemas
from group3.integration.readiness import IntegrationSettings, check_readiness
from tests.test_references import document, reference


@pytest.fixture
def local_store(tmp_path, make_paper):
    store = JsonPaperStore(tmp_path / "source")
    folder = store.begin("handoff", "run1")
    papers = []
    for i in (1,2):
        paper = document(make_paper(i), [reference(doi="10.1234/fixture")])
        path = folder / f"paper{i}.html"
        path.write_bytes(b"Synthetic evidence body")
        paper.raw_document_path = str(path)
        paper.parsed_document_path = str(path)
        paper.raw_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        store.save(folder, paper)
        papers.append(paper)
    store.finish(folder, RetrievalResult(task_id="handoff", run_id="run1", status="completed", requested_count=2,
        selected_count=2, paper_ids=[p.paper_id for p in papers], paper_store_uri=folder.as_uri()))
    return store, papers, StoreSelection(task_id="handoff",run_id="run1")


def test_portable_bundle_roundtrip(tmp_path, local_store):
    store, papers, selection = local_store
    output = tmp_path / "transfer.zip"
    index = export_bundle(store.root,selection,output)
    assert index.papers[0].raw_document_path.startswith("documents/")
    assert not Path(index.papers[0].raw_document_path).is_absolute()
    result = import_bundle(output,tmp_path/"different-machine")
    restored = verified_papers(tmp_path/"different-machine",selection.task_id,selection.run_id)
    assert len(restored) == 2
    assert restored[0].sections == papers[0].sections
    assert restored[0].raw_document_path != papers[0].raw_document_path
    assert Path(restored[0].raw_document_path).read_bytes() == b"Synthetic evidence body"
    assert "different-machine" in result.paper_store_uri


def rewrite_zip(source, target, transform):
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target,"w") as dst:
        for name in src.namelist():
            dst.writestr(name,transform(name,src.read(name)))


@pytest.mark.parametrize("corruption",["content", "path", "metadata_checksum", "selection"])
def test_bundle_corruption_rejected(tmp_path, local_store, corruption):
    store, papers, selection = local_store
    source, bad = tmp_path/"source.zip",tmp_path/"bad.zip"
    export_bundle(store.root,selection,source)
    def transform(name,data):
        if corruption == "content" and name.startswith("documents/"):
            return b"changed source"
        if name == "bundle.json":
            index = json.loads(data)
            if corruption == "path":
                index["papers"][0]["raw_document_path"] = "../escape.html"
            elif corruption == "metadata_checksum":
                index["papers"][0]["raw_sha256"] = "0"*64
            elif corruption == "selection":
                index["selection"]["task_id"] = "another-task"
            return json.dumps(index).encode()
        return data
    rewrite_zip(source,bad,transform)
    with pytest.raises(ValueError):
        import_bundle(bad,tmp_path/"rejected")
    assert not (tmp_path/"rejected").exists()
    assert not (tmp_path/"escape.html").exists()


def test_unexpected_archive_entry_rejected(tmp_path,local_store):
    store, _, selection = local_store
    output=tmp_path/"bundle.zip"
    export_bundle(store.root,selection,output)
    with zipfile.ZipFile(output,"a") as archive:
        archive.writestr("../escape", b"extra")
    with pytest.raises(ValueError,match="unexpected"):
        inspect_bundle(output)


def test_case_insensitive_filename_collision_rejected(tmp_path,local_store):
    store, _, selection = local_store
    source,bad=tmp_path/"source.zip",tmp_path/"bad.zip"
    export_bundle(store.root,selection,source)
    def transform(name,data):
        if name=="bundle.json":
            index=json.loads(data)
            new_name="documents/PAPER1.html"
            index["papers"][1]["raw_document_path"]=new_name
            index["papers"][1]["parsed_document_path"]=new_name
            index["checksums"][new_name]=index["checksums"].pop("documents/paper2.html")
            return json.dumps(index).encode()
        return data
    rewrite_zip(source,bad,transform)
    with pytest.raises(ValueError,match="case-insensitive"):
        inspect_bundle(bad)


def test_duplicate_archive_member_rejected(tmp_path,local_store):
    store, _, selection = local_store
    output=tmp_path/"bundle.zip"
    export_bundle(store.root,selection,output)
    with pytest.warns(UserWarning,match="Duplicate name"):
        with zipfile.ZipFile(output,"a") as archive:
            archive.writestr("bundle.json",b"{}")
    with pytest.raises(ValueError,match="duplicate"):
        inspect_bundle(output)


def test_no_overwrite_export_or_import(tmp_path,local_store):
    store, _, selection = local_store
    output=tmp_path/"bundle.zip"
    export_bundle(store.root,selection,output)
    original=output.read_bytes()
    with pytest.raises(FileExistsError):
        export_bundle(store.root,selection,output)
    assert output.read_bytes() == original
    with pytest.raises(FileExistsError):
        import_bundle(output,store.root)


def test_changed_source_is_rejected(tmp_path,local_store):
    store, papers, selection = local_store
    Path(papers[0].raw_document_path).write_bytes(b"tampered")
    with pytest.raises(ValueError,match="SHA-256"):
        export_bundle(store.root,selection,tmp_path/"bad.zip")


def test_decision_trace_moves_with_portable_store(tmp_path,local_store):
    store,_,selection=local_store
    folder=store.root/selection.task_id/selection.run_id
    path=folder/"decisions.json"
    path.write_text('{"decision":"stop"}',encoding="utf-8")
    result=RetrievalResult.model_validate_json((folder/"manifest.json").read_text(encoding="utf-8"))
    store.finish(folder,result.model_copy(update={"decisions_path":str(path)}))
    output=tmp_path/"trace.zip"
    export_bundle(store.root,selection,output)
    restored=import_bundle(output,tmp_path/"recipient")
    assert Path(restored.decisions_path).read_text(encoding="utf-8")==path.read_text(encoding="utf-8")
    assert restored.decisions_path!=str(path)


def group2_payload(papers):
    evidence = Evidence(evidence_id="e1",paper_id=papers[0].paper_id,section_id="s1",quote="Synthetic evidence body")
    reader = ReaderResult(paper_id=papers[0].paper_id,overview=[Claim(claim_id="c1",text=evidence.quote,evidence_ids=["e1"])])
    return Group2Output(task_id="handoff",run_id="run1",reader_results=[reader],evidence=[evidence],data_provenance="example_fixture")


def test_group2_assembly_uses_verified_store(local_store):
    store,papers,_ = local_store
    payload=group2_payload(papers)
    request,missing=assemble(payload,"fixture topic",store.root)
    assert len(request.papers)==2 and len(request.common_references.common_references)==1
    assert request.data_provenance=="example_fixture" and missing
    assert request.reader_results[0].overview[0].text=="Synthetic evidence body"


@pytest.mark.parametrize("corruption",["quote","paper","run"])
def test_group2_input_rejected(local_store,corruption):
    store,papers,_=local_store
    payload=group2_payload(papers)
    if corruption=="quote":
        payload.evidence[0].quote="fabricated quote"
    elif corruption=="paper":
        payload.paper_ids=["arxiv:2401.99999"]
    else:
        payload.run_id="missing-run"
    with pytest.raises((ValueError,FileNotFoundError)):
        assemble(payload,"fixture topic",store.root)


def test_schema_export_for_consumers(tmp_path):
    names=export_schemas(tmp_path)
    assert "Group2Output.schema.json" in names and "WriterRequest.schema.json" in names
    schema=json.loads((tmp_path/"Group2Output.schema.json").read_text())
    assert "task_id" in schema["required"] and "run_id" in schema["required"]
    assert "quote" in schema["$defs"]["Evidence"]["required"]
    assert "Provisional" in schema["$comment"]


@pytest.mark.parametrize("alive",[True,False])
async def test_readiness_no_key_or_endpoint_secret_leak(local_store,alive):
    store,papers,selection=local_store
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200,text="true" if alive else "false")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result=await check_readiness(Settings(_env_file=None,store_root=store.root),
            AnalysisSettings(_env_file=None,GROQ_API_KEY="secret-fixture"),
            IntegrationSettings(_env_file=None,reader_url="http://example.invalid/?token=secret-fixture"),selection=selection,client=client)
    assert len(calls)==1 and "/api/isalive" in calls[0]
    assert "secret-fixture" not in json.dumps(result)
    assert not result["groq_api_called"] and not result["all_checks_verified"]
    grobid=next(c for c in result["checks"] if c["name"]=="grobid")
    assert grobid["status"]==("passed" if alive else "failed")
