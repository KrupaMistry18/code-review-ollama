# backend/app.py
import os
import re
import json
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ----- env -----
load_dotenv()
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:3.8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ----- app -----
app = FastAPI(title="GenAI Code Review (Ollama)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-friendly; tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# globals (initialized on startup)
llm = None
have_ollama = False

def _try_import_ollama():
    """Defer import so uvicorn can always import this module and find `app`."""
    global have_ollama
    try:
        from langchain_community.chat_models import ChatOllama  # noqa: F401
        from langchain_core.messages import SystemMessage, HumanMessage  # noqa: F401
        have_ollama = True
    except Exception:
        have_ollama = False

_try_import_ollama()

# ---------- Schemas ----------
class ReviewRequest(BaseModel):
    diff: Optional[str] = None
    text: Optional[str] = None
    focus: List[str] = ["security", "performance", "style"]

class Finding(BaseModel):
    category: str
    severity: str
    message: str

class ReviewResult(BaseModel):
    summary: str
    findings: List[Finding]

# ---------- Helpers ----------
CHUNK_MAX_CHARS = 8_000
MAX_REQUEST_LEN = 200_000  # guardrail

def _split_into_chunks(s: str) -> List[str]:
    if not s:
        return []
    parts = re.split(r"(?=^@@.*@@)", s, flags=re.MULTILINE)  # split at diff hunks if present
    if len(parts) == 1:
        return [s[i:i + CHUNK_MAX_CHARS] for i in range(0, len(s), CHUNK_MAX_CHARS)]
    chunks, current = [], ""
    for p in parts:
        if current and len(current) + len(p) > CHUNK_MAX_CHARS:
            chunks.append(current); current = p
        else:
            current += p
    if current:
        chunks.append(current)
    return chunks

SYSTEM_REVIEWER = (
    "You are a senior software reviewer. Be precise, cite concrete lines/snippets from the input, "
    "and focus on actionable, minimal-change suggestions."
)

# === STRICT JSON PROMPT (single-shot) ===
JSON_PROMPT = """Analyze the following code change (diff or source). Focus on: {focus_order}.
Return ONLY valid JSON with this exact schema (no prose, no markdown):

{{
  "summary": [
    "bullet 1",
    "bullet 2",
    "bullet 3",
    "bullet 4",
    "bullet 5"
  ],
  "findings": [
    {{
      "category": "security|performance|style",
      "severity": "High|Medium|Low",
      "message": "short actionable point"
    }}
  ]
}}

Rules:
- summary: 3–5 crisp bullets.
- findings: 3–12 items total; distribute across categories as appropriate.
- message: 1–2 sentences, no headings or code blocks.
- Do NOT include anything outside the JSON object.

INPUT:
{chunk}
"""

def _focus_order(focus: List[str]) -> str:
    order = ["security", "performance", "style"]
    requested = [f for f in order if f in focus]
    tail = [f for f in order if f not in requested]
    return ", ".join([*requested, *tail])

def _ollama_chat(system_text: str, user_text: str) -> str:
    """Call Ollama via LangChain; raises 500 if not initialized."""
    global llm
    if llm is None:
        raise HTTPException(status_code=500, detail="Ollama LLM not initialized")
    from langchain_core.messages import SystemMessage, HumanMessage
    msgs = [SystemMessage(content=system_text), HumanMessage(content=user_text)]
    resp = llm.invoke(msgs)
    return (resp.content or "").strip()

def _extract_json(s: str) -> Dict[str, Any]:
    """Extract first JSON object from a possibly noisy LLM response."""
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        return json.loads(s)
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        raise ValueError("no JSON object found")
    return json.loads(m.group(0))

def _normalize_findings(items):
    seen = set()
    out = []
    for f in items or []:
        try:
            cat = (f.get("category") or "").strip().lower()
            if "security" in cat:
                cat = "security"
            elif "performance" in cat:
                cat = "performance"
            elif "style" in cat:
                cat = "style"
            else:
                continue
            sev = (f.get("severity") or "").strip().title()
            if sev not in {"High", "Medium", "Low"}:
                msg_l = (f.get("message") or "").lower()
                if any(x in msg_l for x in ["critical", "high", "dos"]):
                    sev = "High"
                elif "medium" in msg_l or "moderate" in msg_l:
                    sev = "Medium"
                else:
                    sev = "Low"
            msg = re.sub(r"\s+", " ", (f.get("message") or "")).strip()
            key = (cat, sev, msg.lower())
            if msg and key not in seen:
                seen.add(key)
                out.append({"category": cat, "severity": sev, "message": msg})
        except Exception:
            continue
    return out[:12]

def _to_result(data: Dict[str, Any]) -> ReviewResult:
    summary_list = data.get("summary") or []
    # format bullets into one string (what your client expects)
    summary_text = "\n".join(f"- {re.sub(r'\\s+', ' ', str(x)).strip()}" for x in summary_list[:5]) or "No summary provided."
    findings_list = _normalize_findings(data.get("findings") or [])
    return ReviewResult(
        summary=summary_text,
        findings=[Finding(**f) for f in findings_list]
    )

# ---------- Lifecycle ----------
@app.on_event("startup")
def _startup():
    global llm
    if not USE_OLLAMA:
        print("[startup] USE_OLLAMA is false; API will run but LLM is disabled.")
        return
    if not have_ollama:
        print("[startup] langchain-community not installed; run: pip install langchain-community")
        return
    try:
        from langchain_community.chat_models import ChatOllama
        llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.2)
        print(f"[startup] Using Ollama at {OLLAMA_BASE_URL} with model {OLLAMA_MODEL}")
    except Exception as e:
        llm = None
        print(f"[startup] Failed to init Ollama model: {type(e).__name__}: {e}")

# ---------- Routes ----------
@app.get("/health")
def health():
    return {
        "ok": True,
        "provider": "ollama" if USE_OLLAMA else "none",
        "model": OLLAMA_MODEL if USE_OLLAMA else None,
        "llm_initialized": llm is not None,
    }

@app.post("/review", response_model=ReviewResult)
def review(req: ReviewRequest):
    # pick source text
    src = req.diff or req.text
    if not src:
        raise HTTPException(status_code=400, detail="Provide 'diff' or 'text'.")
    if len(src) > MAX_REQUEST_LEN:
        raise HTTPException(status_code=413, detail=f"Diff too large (> {MAX_REQUEST_LEN} chars). Try a smaller chunk.")
    if not USE_OLLAMA or llm is None:
        raise HTTPException(status_code=500, detail="Ollama not ready. Check service/model and restart.")

    focus_str = _focus_order(req.focus)
    # single-shot over whole text if small; otherwise first chunk (keeps latency down)
    chunk = src if len(src) <= CHUNK_MAX_CHARS else _split_into_chunks(src)[0]

    try:
        user = JSON_PROMPT.format(chunk=chunk, focus_order=focus_str)
        raw = _ollama_chat(SYSTEM_REVIEWER, user)
        data = _extract_json(raw)
        return _to_result(data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"Model returned non-JSON output: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {type(e).__name__}: {e}")
