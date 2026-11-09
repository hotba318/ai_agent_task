import argparse
import asyncio
import json
from pathlib import Path

from group3.common.analysis_schemas import StoreSelection
from group3.common.config import AnalysisSettings, Settings
from .assembler import assemble
from .bundle import export_bundle, import_bundle
from .contracts import Group2Output, export_schemas
from .readiness import IntegrationSettings, check_readiness


def main():
    parser = argparse.ArgumentParser(description="Provisional Group 1/2 handoff tools")
    commands = parser.add_subparsers(dest="command", required=True)
    schemas = commands.add_parser("schemas")
    schemas.add_argument("--output", type=Path, default=Path("docs/contracts"))
    export = commands.add_parser("export-store")
    export.add_argument("--task-id", required=True)
    export.add_argument("--run-id", required=True)
    export.add_argument("--store-root", type=Path)
    export.add_argument("--output", type=Path, required=True)
    load = commands.add_parser("import-store")
    load.add_argument("--input", type=Path, required=True)
    load.add_argument("--store-root", type=Path, required=True)
    assemble_cmd = commands.add_parser("assemble-writer")
    assemble_cmd.add_argument("--input", type=Path, required=True)
    assemble_cmd.add_argument("--topic", required=True)
    assemble_cmd.add_argument("--store-root", type=Path)
    assemble_cmd.add_argument("--output", type=Path, required=True)
    doctor = commands.add_parser("check")
    doctor.add_argument("--task-id")
    doctor.add_argument("--run-id")
    doctor.add_argument("--group2-input", type=Path)
    doctor.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "schemas":
        result = {"provisional": True, "files": export_schemas(args.output)}
    elif args.command == "export-store":
        index = export_bundle(args.store_root or Settings().store_root,
            StoreSelection(task_id=args.task_id, run_id=args.run_id), args.output)
        result = {"bundle": str(args.output.resolve()), "paper_count": len(index.papers)}
    elif args.command == "import-store":
        result = import_bundle(args.input, args.store_root).model_dump(mode="json")
    elif args.command == "assemble-writer":
        source = Group2Output.model_validate_json(args.input.read_text(encoding="utf-8"))
        request, missing = assemble(source, args.topic, args.store_root or Settings().store_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(request.model_dump_json(indent=2), encoding="utf-8")
        result = {"writer_input": str(args.output.resolve()), "data_provenance": request.data_provenance,
                  "selected_count": len(request.papers), "missing_coverage": missing, "evidence_verified": False}
    else:
        if bool(args.task_id) != bool(args.run_id):
            parser.error("--task-id and --run-id must be supplied together")
        selection = StoreSelection(task_id=args.task_id, run_id=args.run_id) if args.task_id else None
        result = asyncio.run(check_readiness(Settings(), AnalysisSettings(), IntegrationSettings(),
            selection=selection, group2_input=args.group2_input))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.command == "check" and not result["ready_for_external_attempt"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
