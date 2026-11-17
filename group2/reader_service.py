from fastapi import FastAPI, HTTPException
from google.genai.errors import APIError

from paper_reader import GeminiPaperReader
from schemas import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    ExtractRequest,
    PaperTemplate,
    PaperStoreEntry,
)
from paper_store import PaperNotFoundError, PaperStore
from group3_contracts import PaperDocument, ReaderAnalysis

app = FastAPI(title="A2A Paper Reader", version="1.0.0")
reader = GeminiPaperReader()
paper_store = PaperStore()


@app.put("/api/v1/papers/{paper_id}", status_code=201)
async def store_paper(paper_id: str, entry: PaperStoreEntry) -> dict[str, str]:
    await paper_store.save(paper_id, entry)
    return {"paper_id": paper_id, "status": "stored"}


@app.post("/api/v1/group3/read", response_model=ReaderAnalysis)
async def read_group3_paper(paper: PaperDocument) -> ReaderAnalysis:
    try:
        return await reader.analyze_group3(paper)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (APIError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/v1/extract", response_model=PaperTemplate)
async def extract_paper(request: ExtractRequest) -> PaperTemplate:
    try:
        title = request.title
        sections = request.sections
        if not title or not sections:
            stored_paper = await paper_store.get(request.paper_id)
            title = title or stored_paper.title
            sections = sections or stored_paper.sections
        return await reader.extract_paper(
            paper_id=request.paper_id,
            title=title,
            sections=sections,
        )
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (APIError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post(
    "/api/v1/verify",
    response_model=ClaimVerificationResult,
)
async def verify_claim(
    request: ClaimVerificationRequest,
) -> ClaimVerificationResult:
    try:
        if request.paper_text:
            verification_request = request
        else:
            stored_paper = await paper_store.get(request.paper_id)
            verification_request = request.model_copy(
                update={"paper_text": "\n\n".join(stored_paper.sections)}
            )
        return await reader.verify_claim(verification_request)
    except PaperNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (APIError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
