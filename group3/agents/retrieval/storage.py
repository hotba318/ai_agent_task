from pathlib import Path
from uuid import uuid4

from group3.common.schemas import PaperDocument, RetrievalResult


class JsonPaperStore:
    """Local development adapter; returned URI is an actual file URI."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def begin(self, task_id: str, run_id: str) -> Path:
        # Defense in depth when used outside validated request entry points.
        for part in (task_id, run_id):
            if not part or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in part):
                raise ValueError("unsafe store identifier")
        folder = self.root / task_id / run_id
        folder.mkdir(parents=True, exist_ok=False)
        return folder

    def write_json(self, path: Path, model):
        temporary = path.with_suffix(f".{uuid4().hex}.tmp")
        temporary.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    def save(self, folder: Path, paper: PaperDocument):
        self.write_json(folder / (self.key(paper.paper_id) + ".json"), paper)

    def finish(self, folder: Path, result: RetrievalResult):
        self.write_json(folder / "manifest.json", result)

    def load(self, folder: Path, paper_id: str) -> PaperDocument:
        return PaperDocument.model_validate_json((folder / (self.key(paper_id) + ".json")).read_text(encoding="utf-8"))

    def list_papers(self, folder: Path) -> list[PaperDocument]:
        manifest = RetrievalResult.model_validate_json((folder / "manifest.json").read_text(encoding="utf-8"))
        return [self.load(folder, pid) for pid in manifest.paper_ids]

    @staticmethod
    def key(paper_id):
        from group3.common.schemas import canonical_arxiv_id
        return canonical_arxiv_id(paper_id).replace(":", "_").replace("/", "_").replace(".", "_")
