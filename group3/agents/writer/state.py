"""Writer-local revision ledger; separate from Supervisor memory and Paper Store."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from group3.common.analysis_schemas import WriterRequest


class RevisionLimitError(ValueError):
    pass


class WriterState:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, request TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0)")
            fields={row[1] for row in db.execute("PRAGMA table_info(reports)")}
            if "initial_result" not in fields:
                db.execute("ALTER TABLE reports ADD COLUMN initial_result TEXT")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, report_id, request, result=None):
        with self.connect() as db:
            db.execute("INSERT INTO reports(id, request, initial_result) VALUES (?,?,?)", (report_id, request.model_dump_json(), result.model_dump_json() if result else None))

    def previous_report(self, report_id):
        import json
        with self.connect() as db:
            row=db.execute("SELECT initial_result FROM reports WHERE id=?",(report_id,)).fetchone()
        return json.loads(row[0])["markdown"] if row and row[0] else None

    def reserve_revision(self, report_id):
        # Atomic check-and-increment across service processes/restarts.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT request, revision FROM reports WHERE id=?", (report_id,)).fetchone()
            if row is None:
                raise ValueError("unknown report_id")
            if row[1] >= 1:
                raise RevisionLimitError("Coverage allows at most one rewrite per report")
            db.execute("UPDATE reports SET revision=1 WHERE id=? AND revision=0", (report_id,))
        return WriterRequest.model_validate_json(row[0])
