"""Portable Paper Store ZIP; file hashes establish transfer integrity, not factual truth."""
import hashlib
import json
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Literal
from uuid import uuid4

from pydantic import Field, model_validator

from group3.agents.retrieval.storage import JsonPaperStore
from group3.common.analysis_schemas import StoreSelection
from group3.common.schemas import Contract, PaperDocument, RetrievalResult
from .assembler import verified_papers

MAX_BUNDLE_BYTES = 200 * 1024 * 1024


class BundleIndex(Contract):
    format: Literal["group3-paper-store-zip-v1"] = "group3-paper-store-zip-v1"
    selection: StoreSelection
    retrieval: RetrievalResult
    papers: list[PaperDocument]
    checksums: dict[str, str]

    @model_validator(mode="after")
    def consistency(self):
        if (self.selection.task_id, self.selection.run_id) != (self.retrieval.task_id, self.retrieval.run_id):
            raise ValueError("bundle selection/manifest mismatch")
        ids = [p.paper_id for p in self.papers]
        if ids != self.retrieval.paper_ids or self.selection.paper_ids != ids:
            raise ValueError("bundle papers disagree with selected manifest")
        paths = {name for p in self.papers for name in (p.raw_document_path, p.parsed_document_path)}
        if self.retrieval.decisions_path:
            paths.add(self.retrieval.decisions_path)
        if paths != self.checksums.keys():
            raise ValueError("bundle source file index mismatch")
        if len({name.casefold() for name in paths}) != len(paths):
            raise ValueError("bundle filenames collide on case-insensitive filesystems")
        for name in paths:
            if not re.fullmatch(r"documents/[A-Za-z0-9_.-]+", name) or ".." in PurePosixPath(name).parts:
                raise ValueError("unsafe bundle document path")
        for checksum in self.checksums.values():
            if not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ValueError("invalid checksum")
        return self


def export_bundle(store_root: Path, selection: StoreSelection, output: Path):
    if selection.paper_ids:
        raise ValueError("bundle export preserves the full run; paper_ids must be empty")
    papers = verified_papers(store_root, selection.task_id, selection.run_id)
    folder = store_root.resolve() / selection.task_id / selection.run_id
    original = RetrievalResult.model_validate_json((folder / "manifest.json").read_text(encoding="utf-8"))
    if [p.paper_id for p in papers] != original.paper_ids:
        raise ValueError("paper metadata/manifest mismatch")
    output = output.resolve()
    if output.exists():
        raise FileExistsError("bundle output already exists")
    sources, portable = {}, []
    for paper in papers:
        changes = {}
        for field in ("raw_document_path", "parsed_document_path"):
            path = Path(getattr(paper, field)).resolve()
            name = "documents/" + path.name
            content = path.read_bytes()
            if name in sources and sources[name] != content:
                raise ValueError("source filename collision")
            sources[name] = content
            changes[field] = name
        portable.append(paper.model_copy(update=changes))
    if sum(map(len, sources.values())) > MAX_BUNDLE_BYTES:
        raise ValueError("bundle is larger than allowed limit")
    changes={"paper_store_uri":output.as_uri()}
    if original.decisions_path:
        decision_path=Path(original.decisions_path).resolve()
        if not decision_path.is_relative_to(folder.resolve()) or not decision_path.is_file():
            raise ValueError("retrieval decision artifact is missing or outside source run")
        relative="documents/retrieval-decisions.json"
        sources[relative]=decision_path.read_bytes()
        changes["decisions_path"]=relative
    result = original.model_copy(update=changes)
    index = BundleIndex(selection=selection.model_copy(update={"paper_ids": original.paper_ids}), retrieval=result,
        papers=portable, checksums={name: hashlib.sha256(value).hexdigest() for name, value in sources.items()})
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + "." + uuid4().hex + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("bundle.json", index.model_dump_json(indent=2))
            for name, value in sources.items():
                archive.writestr(name, value)
        # Exclusive destination creation avoids overwriting a concurrent export.
        with output.open("xb") as destination, temporary.open("rb") as source:
            import shutil
            shutil.copyfileobj(source, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return index


def inspect_bundle(path: Path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or sum(info.file_size for info in infos) > MAX_BUNDLE_BYTES:
            raise ValueError("duplicate entries or oversized bundle")
        if any(stat.S_ISLNK(info.external_attr >> 16) for info in infos):
            raise ValueError("bundle symlinks are not supported")
        if "bundle.json" not in names:
            raise ValueError("missing bundle index")
        index = BundleIndex.model_validate_json(archive.read("bundle.json"))
        if set(names) != {"bundle.json", *index.checksums}:
            raise ValueError("unexpected bundle entries")
        files = {name: archive.read(name) for name in index.checksums}
        for name, value in files.items():
            if hashlib.sha256(value).hexdigest() != index.checksums[name]:
                raise ValueError("bundle SHA-256 mismatch")
        for paper in index.papers:
            if index.checksums[paper.raw_document_path] != paper.raw_sha256:
                raise ValueError("bundle raw document checksum disagrees with paper metadata")
    return index, files


def import_bundle(path: Path, store_root: Path):
    index, files = inspect_bundle(path)
    store = JsonPaperStore(store_root)
    target = (store.root / index.selection.task_id / index.selection.run_id).resolve()
    if not target.is_relative_to(store.root):
        raise ValueError("import target escapes configured root")
    if target.exists():
        raise FileExistsError("Paper Store run already exists; refusing overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".bundle-import-", dir=store.root) as staging_name:
        staging = Path(staging_name).resolve()
        if not staging.is_relative_to(store.root):
            raise ValueError("staging target escapes configured root")
        for name, value in files.items():
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(value)
        for paper in index.papers:
            rebased = paper.model_copy(update={field: str(target / getattr(paper, field))
                for field in ("raw_document_path", "parsed_document_path")})
            store.save(staging, rebased)
        updates={"paper_store_uri":target.as_uri()}
        if index.retrieval.decisions_path:
            updates["decisions_path"]=str(target/index.retrieval.decisions_path)
        result = index.retrieval.model_copy(update=updates)
        store.finish(staging, result)
        staging.rename(target)
    return result
