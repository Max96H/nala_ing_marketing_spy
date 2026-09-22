"""
ING Banking Campaigns Comparator — API backend

Serves everything in data/bank_analysis.db as JSON for the React app in app/, and
proxies chatbot requests to Groq (keeps the API key server-side — it's
never sent to the browser).

Run collector.py -> analyst.py -> analysis.py -> change_watcher.py (or
main.py) BEFORE starting this — it only reads what's already in the
database, it doesn't scrape or analyze anything itself.

Setup:
    pip install fastapi uvicorn python-dotenv groq --break-system-packages
    export GROQ_API_KEY=gsk_...  (or use a .env file)

Usage:
    uvicorn api:app --reload --port 8000
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent / "src"))
import assistant  # reuse load_context(), SYSTEM_PROMPT, MODEL — don't reimplement the chat logic

load_dotenv()

DB_PATH = "data/bank_analysis.db"

app = FastAPI(title="ING Campaign Comparator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn() -> sqlite3.Connection:
    if not Path(DB_PATH).exists():
        raise HTTPException(status_code=503, detail=f"No database found at {DB_PATH} yet. "
                                                      "Run the pipeline first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def rows_from(table: str) -> list[dict]:
    conn = get_conn()
    if not table_exists(conn, table):
        conn.close()
        return []
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
    conn.close()
    return rows


@app.get("/api/pages")
def get_pages():
    return rows_from("pages")


@app.get("/api/positioning")
def get_positioning():
    return rows_from("positioning")


@app.get("/api/radar")
def get_radar():
    return rows_from("radar_scores")


@app.get("/api/changes")
def get_changes():
    return rows_from("changes")


@app.get("/api/gaps")
def get_gaps():
    return rows_from("gaps")


@app.get("/api/summary")
def get_summary():
    conn = get_conn()
    pages = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    banks = conn.execute("SELECT COUNT(DISTINCT bank) FROM pages").fetchone()[0]
    analyzed = conn.execute(
        "SELECT COUNT(*) FROM pages WHERE tone IS NOT NULL AND tone != ''"
    ).fetchone()[0]
    changes = conn.execute(
        "SELECT COUNT(*) FROM changes"
    ).fetchone()[0] if table_exists(conn, "changes") else 0
    conn.close()
    return {"pages": pages, "banks": banks, "analyzed": analyzed, "changes": changes}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]  # full history, most recent user message last


@app.post("/api/chat")
def chat(req: ChatRequest):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set on the server.")

    from groq import Groq
    client = Groq(api_key=api_key)

    conn = get_conn()
    context = assistant.load_context(conn)
    conn.close()

    full_messages = [{"role": "system", "content": f"{assistant.SYSTEM_PROMPT}\n\n{context}"}]
    full_messages += [{"role": m.role, "content": m.content} for m in req.messages]

    response = client.chat.completions.create(
        model=assistant.MODEL,
        max_tokens=1000,
        messages=full_messages,
    )
    answer = response.choices[0].message.content.strip()
    return {"role": "assistant", "content": answer}