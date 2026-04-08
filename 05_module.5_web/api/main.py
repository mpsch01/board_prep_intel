"""
Board Prep Intel — PDF Score Parser Microservice
Deploy on Railway (or Render).  Single-purpose: parse ABFM ITE score report
PDFs and write item-level results to Supabase.

Routes:
    GET  /health           — health check
    POST /parse-score-report — download PDF from Supabase Storage, parse, write scores

Environment variables:
    SUPABASE_URL             https://xxxxx.supabase.co
    SUPABASE_SERVICE_KEY     eyJhbGc...  (service_role — bypasses RLS)
    PARSER_SECRET            shared secret for request authentication

Dependencies (see requirements.txt):
    fastapi, uvicorn, supabase, PyMuPDF, python-dotenv, httpx
"""

import hashlib
import hmac
import logging
import os
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
PARSER_SECRET = os.environ.get("PARSER_SECRET", "")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Board Prep Intel — Score Parser",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Netlify will call this; restrict in production
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ParseRequest(BaseModel):
    upload_id: int
    resident_id: str          # Supabase user UUID
    exam_year: int
    storage_path: str         # e.g. score-reports/{uid}/{year}/filename.pdf


class ParseResponse(BaseModel):
    upload_id: int
    items_parsed: int
    status: str


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------
def verify_secret(x_parser_secret: str) -> None:
    """Constant-time comparison of the shared secret."""
    if not PARSER_SECRET:
        return  # secret not configured — allow all (development only)
    if not hmac.compare_digest(x_parser_secret or "", PARSER_SECRET):
        raise HTTPException(status_code=401, detail="Invalid parser secret")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/parse-score-report", response_model=ParseResponse)
async def parse_score_report(
    payload: ParseRequest,
    x_parser_secret: str = Header(default="", alias="X-Parser-Secret"),
):
    verify_secret(x_parser_secret)
    log.info(f"Parsing upload {payload.upload_id} for resident {payload.resident_id}")

    # ── Update upload status → processing ───────────────────────────────────
    supabase.table("score_uploads").update({"parse_status": "processing"}).eq(
        "id", payload.upload_id
    ).execute()

    try:
        # ── Download PDF from Supabase Storage ────────────────────────────────
        pdf_bytes = _download_from_storage(payload.storage_path)

        # ── Parse PDF ─────────────────────────────────────────────────────────
        items = _parse_pdf(pdf_bytes, payload.exam_year)

        # ── Map item numbers to QIDs ───────────────────────────────────────────
        scored_items = _map_items_to_qids(items, payload.exam_year)

        # ── Write to resident_scores ───────────────────────────────────────────
        _write_scores(payload.resident_id, payload.exam_year, scored_items)

        # ── Update upload status → complete ───────────────────────────────────
        from datetime import datetime, timezone
        supabase.table("score_uploads").update(
            {
                "parse_status": "complete",
                "items_parsed": len(scored_items),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", payload.upload_id).execute()

        log.info(f"Upload {payload.upload_id}: parsed {len(scored_items)} items")
        return ParseResponse(
            upload_id=payload.upload_id,
            items_parsed=len(scored_items),
            status="complete",
        )

    except Exception as exc:
        log.exception(f"Upload {payload.upload_id} failed: {exc}")
        supabase.table("score_uploads").update(
            {"parse_status": "failed", "parse_error": str(exc)}
        ).eq("id", payload.upload_id).execute()
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _download_from_storage(storage_path: str) -> bytes:
    """Download a file from Supabase Storage and return raw bytes."""
    response = supabase.storage.from_("score-reports").download(storage_path)
    if isinstance(response, (bytes, bytearray)):
        return bytes(response)
    raise ValueError(f"Unexpected storage response type: {type(response)}")


def _parse_pdf(pdf_bytes: bytes, exam_year: int) -> list[dict]:
    """
    Parse ITE score report PDF using the existing ite_parser module.

    The parser was designed to read from file paths, so we write the bytes
    to a temp file before calling it.

    Returns a list of item dicts:
        [{item: int, correct: bool, blueprint: str, body_system: str|None}, ...]
    """
    import sys
    # ite_parser.py lives in 03_module.3_analyst/scripts/
    # When deployed on Railway, copy the parser to this repo's api/parser/ directory.
    parser_dir = Path(__file__).parent / "parser"
    if str(parser_dir) not in sys.path:
        sys.path.insert(0, str(parser_dir))

    try:
        from ite_parser import parse_blueprint, load_config
        config = load_config(str(parser_dir / "ite_parser_config.json"))
    except ImportError:
        raise RuntimeError(
            "ite_parser.py not found. Copy 03_module.3_analyst/scripts/ite_parser.py "
            "and ite_parser_config.json into api/parser/ before deploying."
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        result = parse_blueprint(tmp_path, config)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    items = result.get("items", [])
    return [
        {
            "item": it["item"],
            "correct": it["correct"],
            "blueprint": it.get("blueprint"),
            "body_system": None,  # body system comes from a separate PDF; populated later
        }
        for it in items
    ]


def _map_items_to_qids(items: list[dict], exam_year: int) -> list[dict]:
    """
    Map item numbers to QIDs using the questions table.

    The ITE score report uses 1-indexed item numbers that correspond to the
    order questions appear in the exam for that year.  We match on exam_year
    and item position ordering.

    NOTE: This mapping is approximate — ABFM does not publish an official
    item-number-to-QID mapping.  We order questions by QID suffix (NNNN)
    which reflects the exam order in our DB.
    """
    response = (
        supabase.table("questions")
        .select("qid, body_system_merged, blueprint")
        .eq("exam_year", exam_year)
        .order("qid")
        .execute()
    )

    question_rows: list[dict] = response.data or []

    # Build a 1-indexed lookup (item 1 = first question in exam_year order)
    item_to_question: dict[int, dict] = {}
    for idx, row in enumerate(question_rows, start=1):
        item_to_question[idx] = row

    scored = []
    for it in items:
        q = item_to_question.get(it["item"])
        scored.append(
            {
                "item_number": it["item"],
                "qid": q["qid"] if q else None,
                "answered_correct": it["correct"],
                "blueprint": it["blueprint"] or (q["blueprint"] if q else None),
                "body_system": q["body_system_merged"] if q else None,
            }
        )
    return scored


def _write_scores(resident_id: str, exam_year: int, items: list[dict]) -> None:
    """Upsert item-level scores into resident_scores."""
    if not items:
        return

    rows = [
        {
            "resident_id": resident_id,
            "exam_year": exam_year,
            "item_number": it["item_number"],
            "qid": it["qid"],
            "answered_correct": it["answered_correct"],
            "blueprint": it["blueprint"],
            "body_system": it["body_system"],
        }
        for it in items
    ]

    # Upsert in batches of 500
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        supabase.table("resident_scores").upsert(rows[i : i + batch_size]).execute()
