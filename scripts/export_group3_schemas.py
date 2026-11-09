"""Export only Group 3 agent input/output schemas."""
import json
from pathlib import Path

from group3.common.analysis_schemas import ReferencesRequest, ReferencesResult, RevisionRequest, WriterRequest, WriterResult
from group3.common.schemas import PaperDocument, RetrievalRequest, RetrievalResult


def main():
    folder=Path("docs/contracts")
    folder.mkdir(parents=True,exist_ok=True)
    models=(RetrievalRequest,RetrievalResult,PaperDocument,ReferencesRequest,ReferencesResult,WriterRequest,RevisionRequest,WriterResult)
    for model in models:
        schema=model.model_json_schema()
        schema["$comment"]="Provisional Group 3 agent contract; requires team agreement."
        (folder/(model.__name__+".schema.json")).write_text(json.dumps(schema,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Exported {len(models)} Group 3 schemas to {folder}")


if __name__=="__main__":
    main()
