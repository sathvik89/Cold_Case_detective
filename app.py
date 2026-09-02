"""
Web UI for the cold case investigator.

Same pipeline as main.py - services/loader reads the evidence files,
services/embedder vectorises them, services/retriever does the FAISS search,
services/llm writes the report - but it runs in the browser and you can add or
remove evidence without touching the data folder by hand.

    uvicorn app:app --reload
    -> http://localhost:8000
"""

import os
import re
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import providers

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
TOP_K = 2

load_dotenv()

app = FastAPI(title="Cold Case Investigator")

# The retriever holds every embedding in memory. It is rebuilt whenever the
# evidence folder changes, which is cheap at this size.
_retriever = None
_lock = Lock()


class Question(BaseModel):
    question: str
    provider: str | None = None
    api_key: str | None = None
    model: str | None = None


class ModelQuery(BaseModel):
    provider: str
    api_key: str | None = None


def safe_name(name: str) -> str:
    """Keep uploads inside the data folder - no paths, no traversal."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)


def build_retriever():
    """
    Imported lazily: services.embedder loads a sentence-transformers model at
    import time, and doing that at startup would stall the first page load.
    """
    from services.loader import load_documents
    from services.embedder import embed_documents
    from services.retriever import Retriever

    docs = load_documents(str(DATA_DIR))
    if not docs:
        return None
    return Retriever(embed_documents(docs))


def get_retriever():
    global _retriever
    with _lock:
        if _retriever is None:
            _retriever = build_retriever()
        return _retriever


def invalidate():
    global _retriever
    with _lock:
        _retriever = None


def list_evidence():
    if not DATA_DIR.exists():
        return []
    files = []
    for path in sorted(DATA_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        files.append(
            {
                "name": path.name,
                "words": len(text.split()),
                "preview": text.strip()[:220],
            }
        )
    return files


@app.get("/api/evidence")
def evidence():
    return {"ok": True, "files": list_evidence()}


@app.get("/api/providers")
def list_providers():
    return {
        "ok": True,
        "default": providers.DEFAULT_PROVIDER,
        "providers": [
            {
                "id": pid,
                "label": spec["label"],
                "default_model": spec["default_model"],
                "console": spec["console"],
                "has_env_key": bool(providers.env_key(pid)),
            }
            for pid, spec in providers.PROVIDERS.items()
        ],
    }


@app.post("/api/models")
def models(payload: ModelQuery):
    try:
        provider, key, _ = providers.resolve(payload.provider, payload.api_key, None)
        return {"ok": True, "models": providers.list_models(provider, key)}
    except providers.ProviderError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": providers.friendly_error(exc)}


@app.post("/api/evidence")
async def add_evidence(file: UploadFile = File(...)):
    name = safe_name(file.filename or "")
    if not name.lower().endswith(".txt"):
        return {"ok": False, "error": "Evidence files have to be .txt"}

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    if not text.strip():
        return {"ok": False, "error": "That file is empty."}

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / name).write_text(text, encoding="utf-8")
    invalidate()  # the new file has to be embedded before the next question
    return {"ok": True, "name": name, "files": list_evidence()}


@app.delete("/api/evidence/{name}")
def remove_evidence(name: str):
    path = DATA_DIR / safe_name(name)
    if not path.exists():
        return {"ok": False, "error": "No such evidence file."}
    path.unlink()
    invalidate()
    return {"ok": True, "files": list_evidence()}


@app.post("/api/ask")
def ask(payload: Question):
    question = payload.question.strip()
    if not question:
        return {"ok": False, "error": "Ask a question first."}

    try:
        retriever = get_retriever()
    except Exception as exc:
        return {"ok": False, "error": f"Could not index the evidence: {exc}"}

    if retriever is None:
        return {
            "ok": False,
            "error": "There is no evidence to search. Add a .txt file first.",
        }

    try:
        provider, key, model = providers.resolve(
            payload.provider, payload.api_key, payload.model
        )
    except providers.ProviderError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        from services.embedder import embed_query
        from services.llm import build_prompt

        query_vector = embed_query(question)
        docs = retriever.search(query_vector, top_k=TOP_K)

        completion = providers.client_for(provider, key).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": build_prompt(question, docs)}],
            temperature=0.1,
        )
        report = providers.clean(completion.choices[0].message.content or "")
    except Exception as exc:
        return {"ok": False, "error": providers.friendly_error(exc)}

    return {
        "ok": True,
        "report": report,
        "model": model,
        "sources": [
            {"source": d["source"], "score": round(d["score"], 3), "content": d["content"]}
            for d in docs
        ],
    }


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
