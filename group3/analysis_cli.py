import argparse
import asyncio
from pathlib import Path

from group3.common.analysis_schemas import ReferencesRequest, RevisionRequest, WriterRequest
from group3.common.config import AnalysisSettings, Settings
from group3.services import analyze_references, write_report


def main():
    parser = argparse.ArgumentParser(description="Standalone Agent 2 / Agent 4")
    sub = parser.add_subparsers(dest="command", required=True)
    references = sub.add_parser("references")
    references.add_argument("--task-id", required=True)
    references.add_argument("--run-id", required=True)
    references.add_argument("--minimum", type=int, default=2)
    references.add_argument("--output", type=Path, required=True)
    for command in ("write", "revise"):
        child = sub.add_parser(command)
        child.add_argument("--input", type=Path, required=True)
        child.add_argument("--mode", choices=["extractive", "groq"])
        child.add_argument("--output-root", type=Path)
        child.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.command == "references":
        result = analyze_references(ReferencesRequest(task_id=args.task_id, run_id=args.run_id,
            min_citing_papers=args.minimum), Settings())
        output = args.output
        summary = f"Common references: {len(result.common_references)}; possible duplicates: {len(result.possible_duplicates)}"
    else:
        model = WriterRequest if args.command == "write" else RevisionRequest
        request = model.model_validate_json(args.input.read_text(encoding="utf-8-sig"))
        settings = AnalysisSettings()
        if args.mode:
            settings.writer_mode = args.mode
        if args.output_root:
            settings.output_root = args.output_root
        result = asyncio.run(write_report(request, settings))
        output = args.result
        summary = f"Report {result.report_id} revision {result.revision}: {result.status}\n{result.markdown_path}"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
