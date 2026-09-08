from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from app.agents.desk import run_desk
from app.agents.runtime import openai_ready
from app.agents.session import save_report
from app.engine import calculate_from_files
from app.money import D
from app.nbp import NbpClient
from app import settings

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "sample_data"

app = FastAPI(
    title="Belka — Polish investment tax",
    description="FIFO + live NBP T-1 capital gains helper, with FX and tax agents.",
    version="1.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Belka Polish investment tax calculator",
        "docs": "/docs",
        "health": "/api/health",
        "ui": "http://localhost:5173",
        "rates": "live NBP Table A+B, no cache",
    }


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "investment-tax",
        "nbp": "live",
        "openai_configured": openai_ready(),
        "llm_key_kind": settings.key_kind(),
        "model": settings.CURSOR_MODEL if settings.key_kind() == "cursor" else (settings.OPENAI_MODEL if openai_ready() else None),
    }


@app.get("/api/samples")
async def list_samples():
    files = sorted(path.name for path in SAMPLES.glob("*") if path.is_file())
    return {
        "files": files,
        "generic_columns": [
            "date",
            "type",
            "symbol",
            "isin",
            "quantity",
            "price",
            "currency",
            "fee",
            "withholding_tax",
            "country",
            "broker",
            "notes",
        ],
    }


@app.get("/api/samples/{name}")
async def download_sample(name: str):
    path = (SAMPLES / name).resolve()
    if not str(path).startswith(str(SAMPLES.resolve())) or not path.exists():
        raise HTTPException(status_code=404, detail="Sample not found")
    return FileResponse(path, filename=path.name)


@app.get("/api/nbp/table/{on_date}")
async def nbp_table(on_date: date, table: str = "A"):
    kind = table.upper()
    if kind not in {"A", "B"}:
        raise HTTPException(status_code=400, detail="table must be A or B")
    try:
        result = NbpClient().fetch_daily_table(on_date, kind)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"NBP did not publish table {kind} on {on_date.isoformat()}")
    return result


@app.get("/api/nbp/rate/{code}")
async def nbp_rate(code: str, on_date: date, mode: str = "t_minus_1"):
    if mode not in {"t_minus_1", "published"}:
        raise HTTPException(status_code=400, detail="mode must be t_minus_1 or published")
    try:
        return NbpClient().convert(D(1), code, on_date, mode=mode)
    except (RuntimeError, LookupError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/calculate")
async def calculate(
    files: list[UploadFile] = File(...),
    tax_year: int = Form(...),
    prior_losses_pln: float = Form(0),
    account_currency: str = Form("PLN"),
    session_id: str = Form("default"),
):
    if not 2000 <= tax_year <= 2100:
        raise HTTPException(status_code=400, detail="tax_year looks invalid")
    uploads: list[tuple[str, bytes]] = []
    for file in files:
        payload = await file.read()
        if not payload:
            continue
        uploads.append((file.filename or "upload.csv", payload))
    if not uploads:
        raise HTTPException(status_code=400, detail="Please upload at least one broker file")
    try:
        report = calculate_from_files(
            uploads,
            tax_year=tax_year,
            prior_losses_pln=D(prior_losses_pln),
            account_currency=account_currency.upper(),
            use_live_nbp=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    save_report(session_id, report)
    return JSONResponse(report.model_dump())


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str = "default"
    messages: list[ChatMessage]
    api_key: str | None = None
    language: str = "pl"


@app.post("/api/chat")
async def chat(body: ChatRequest, x_openai_key: str | None = Header(default=None)):
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages required")
    key = (body.api_key or x_openai_key or "").strip() or None
    if not openai_ready(key):
        raise HTTPException(
            status_code=401,
            detail="Add CURSOR_API_KEY or LLM_API_KEY to backend/.env, or paste a Cursor user API key in the chat panel.",
        )
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in body.messages[-12:]
        if msg.role in {"user", "assistant"} and msg.content.strip()
    ]
    try:
        return run_desk(history, session_id=body.session_id, api_key=key, language=body.language)
    except RuntimeError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Agent failed: {exc}") from exc


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
