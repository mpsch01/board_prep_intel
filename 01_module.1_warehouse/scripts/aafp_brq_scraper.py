#!/usr/bin/env python3
"""
AAFP Board Review Questions Scraper v3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Architecture (discovered from takeClinicalQuestion.js):
  1. GET  /assessment/take/{assessment_id}/c/{question_id}
         → HTML with question stem + answer choices (radio buttons)
  2. POST same URL with selected radio value
         → JSON: {IsCorrect, AnswerExplanation, NextQuestionId,
                  CorrectAnswerIndicators, ScorePercentage, ...}
  3. Follow NextQuestionId to advance — no sequential guessing needed

RUN ON YOUR LOCAL WINDOWS MACHINE — NOT IN THE VM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SETUP (one-time, PowerShell from this folder):
  pip install requests beautifulsoup4

MODES — run in order:
  python aafp_brq_scraper.py --explore     ← validate auth + see one JSON response
  python aafp_brq_scraper.py --discover    ← find all quiz assessment IDs
  python aafp_brq_scraper.py --scrape      ← full extraction → staging JSON

Cookie file (aafp_cookies.json) is already in this folder.
"""

import re
import json
import time
import sys
from pathlib import Path
from html.parser import HTMLParser

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "-q"])
    import requests
    from bs4 import BeautifulSoup

# ══════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════
SCRIPT_DIR    = Path(__file__).resolve().parent
COOKIE_FILE   = SCRIPT_DIR / "aafp_cookies.json"

FIRST_ASSESSMENT_ID = 13882   # "Board Review Questions 01"
FIRST_QUESTION_ID   = 49733   # Q1 of quiz 01
QUESTIONS_PER_QUIZ  = 10
MAX_PROBE_IDS       = 300
REQUEST_DELAY       = 1.2     # seconds between requests

# Known first question IDs (overrides redirect resolution — prevents skipping
# questions that were already touched during explore/testing)
KNOWN_FIRST_QUESTIONS = {
    13882: 49733,   # Board Review Questions 01 — confirmed from explore
}

OUTPUT_DIR    = SCRIPT_DIR / "_aafp_staging"             # scripts/_aafp_staging/ (created on run)
OUTPUT_FILE   = OUTPUT_DIR / "aafp_brq_staging.json"
DUMP_FILE     = SCRIPT_DIR / "aafp_explore_dump.txt"
QUIZ_MAP_FILE = SCRIPT_DIR / "aafp_quiz_map.json"       # place from _archive_/02_question_bank/aafp_initial_staging/ if re-scraping
# ══════════════════════════════════════════════════════════════════════

BASE_URL  = "https://www.aafp.org/assessment/take/{assessment_id}/c/{question_id}"
INTRO_URL = "https://www.aafp.org/assessment/take/{assessment_id}/introduction/c"


def strip_html(html_str: str) -> str:
    """Strip HTML tags and decode entities from a string."""
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.get_text(separator=" ", strip=True)


# ─────────────────────────────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    if not COOKIE_FILE.exists():
        print(f"ERROR: Cookie file not found: {COOKIE_FILE}")
        sys.exit(1)

    with open(COOKIE_FILE, encoding="utf-8") as f:
        cookies_json = json.load(f)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.aafp.org/",
    })
    for c in cookies_json:
        session.cookies.set(
            c["name"], c["value"],
            domain=c.get("domain", ".aafp.org"),
            path=c.get("path", "/"),
        )

    print(f"  Loaded {len(cookies_json)} cookies")
    return session


# ─────────────────────────────────────────────────────────────────────
# STEP 1: GET question page → extract stem + choices
# ─────────────────────────────────────────────────────────────────────
def get_question_html(session: requests.Session, url: str) -> dict | None:
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            return None
        if "Board Review" not in resp.text and "Question" not in resp.text:
            return None
    except Exception as e:
        print(f"    GET error: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Quiz title + question number
    h1 = soup.find("h1")
    quiz_title = h1.get_text(strip=True) if h1 else ""
    counter = soup.find(class_=re.compile("counter"))
    counter_text = counter.get_text(strip=True) if counter else ""
    q_match = re.search(r"Question\s+(\d+)\s+of\s+(\d+)", counter_text)
    question_number = int(q_match.group(1)) if q_match else None
    questions_total = int(q_match.group(2)) if q_match else QUESTIONS_PER_QUIZ

    # Question stem — the <div> inside fieldset before the radio list
    fieldset = soup.find("fieldset")
    stem = ""
    if fieldset:
        # First adl-space div contains the stem
        stem_div = fieldset.find("div", class_=re.compile("adl-space"))
        if stem_div:
            stem = stem_div.get_text(separator=" ", strip=True)

    # Answer choices: value → text
    choices = []
    for radio in soup.find_all("input", {"type": "radio"}):
        value = radio.get("value", "")
        rid   = radio.get("id", "")
        label = soup.find("label", {"for": rid})
        text  = label.get_text(strip=True) if label else (
            radio.parent.get_text(strip=True) if radio.parent else "")
        choices.append({"value": value, "text": text})

    # CSRF token (needed for POST)
    rvt = soup.find("input", {"name": "__RequestVerificationToken"})
    csrf_token = rvt["value"] if rvt else None

    # Hidden form fields needed for POST
    assessment_number = soup.find("input", {"id": "AssessmentNumber"})
    assessment_id_input = soup.find("input", {"id": "AssessmentId"})
    question_id_input = soup.find("input", {"id": "Question_Id"})

    return {
        "quiz_title":      quiz_title,
        "question_number": question_number,
        "questions_total": questions_total,
        "stem":            stem,
        "choices":         choices,
        "csrf_token":      csrf_token,
        "form_assessment_number": assessment_number["value"] if assessment_number else "",
        "form_assessment_id":     assessment_id_input["value"] if assessment_id_input else "",
        "form_question_id":       question_id_input["value"] if question_id_input else "",
    }


# ─────────────────────────────────────────────────────────────────────
# STEP 2: POST answer → get JSON with explanation + next question ID
# ─────────────────────────────────────────────────────────────────────
def post_answer(session: requests.Session, url: str, html_data: dict,
                answer_value: str) -> dict | None:
    """
    POST the selected answer and return the server's JSON response.
    JSON keys (from takeClinicalQuestion.js):
      IsCorrect, AnswerExplanation, NextQuestionId,
      CorrectAnswerIndicators, ScorePercentage, ScoreDecimal,
      AllowMultipleAnswerAttempts, ShowCorrectAnswers
    """
    question_id = url.split("/c/")[-1]
    form_data = {
        f"ClinicalAnswer|{question_id}": answer_value,
        "AssessmentNumber": html_data["form_assessment_number"],
        "AssessmentId":     html_data["form_assessment_id"],
        "Question.Id":      html_data["form_question_id"],
    }
    if html_data.get("csrf_token"):
        form_data["__RequestVerificationToken"] = html_data["csrf_token"]

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": url,
    }

    try:
        resp = session.post(url, data=form_data, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"    POST {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"    POST error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────
# STEP 3: Extract ref + explanation from JSON response
# ─────────────────────────────────────────────────────────────────────
def parse_answer_json(json_resp: dict, choices: list) -> dict:
    """Parse the server JSON into clean fields."""
    explanation_html = json_resp.get("AnswerExplanation", "") or ""
    explanation_text = strip_html(explanation_html)

    # Extract Ref: citation from explanation
    ref_text = ""
    ref_match = re.search(r"Ref:\s*([\s\S]+?)(?:\s{2,}|$)", explanation_text)
    if ref_match:
        ref_text = ref_match.group(1).strip()
    # Clean up explanation (remove the Ref: part)
    explanation_clean = re.sub(r"\s*Ref:.*", "", explanation_text, flags=re.DOTALL).strip()

    # Correct answer
    is_correct = json_resp.get("IsCorrect", False)
    correct_indicators = json_resp.get("CorrectAnswerIndicators", "") or ""
    # correct_indicators may be "A" or choice text or the radio value — TBD after first run

    return {
        "is_correct_on_first_try": is_correct,
        "correct_indicators":     correct_indicators,
        "explanation_html":       explanation_html,
        "explanation":            explanation_clean,
        "ref_text":               ref_text,
        "next_question_id":       json_resp.get("NextQuestionId"),
        "score_pct":              json_resp.get("ScorePercentage", ""),
        "allow_retry":            json_resp.get("AllowMultipleAnswerAttempts", False),
        "show_correct":           json_resp.get("ShowCorrectAnswers", False),
        "_raw_json":              json_resp,
    }


# ─────────────────────────────────────────────────────────────────────
# FULL QUESTION FETCH (GET + POST until correct answer found)
# ─────────────────────────────────────────────────────────────────────
def fetch_question(session: requests.Session, assessment_id: int,
                   question_id: int) -> dict | None:
    url = BASE_URL.format(assessment_id=assessment_id, question_id=question_id)

    # GET: stem + choices
    html_data = get_question_html(session, url)
    if not html_data or not html_data["choices"]:
        return None

    choices = html_data["choices"]

    # POST each choice until IsCorrect = True.
    # NOTE: AnswerExplanation is ONLY populated on the correct-answer response.
    # Capture explanation from whichever response has it (prioritize correct response).
    explanation      = ""
    explanation_html = ""
    ref_text         = ""
    next_qid         = None
    correct_value    = None
    first_resp       = None

    for i, choice in enumerate(choices):
        json_resp = post_answer(session, url, html_data, choice["value"])
        if json_resp is None:
            break

        if first_resp is None:
            first_resp = json_resp

        is_correct = json_resp.get("IsCorrect", False)

        # Capture explanation from any response that has it;
        # re-capture when we hit IsCorrect (may be more complete).
        raw_expl = json_resp.get("AnswerExplanation") or ""
        if raw_expl and (not explanation or is_correct):
            answer_data      = parse_answer_json(json_resp, choices)
            explanation      = answer_data["explanation"]
            explanation_html = raw_expl          # preserve raw HTML for re-processing
            ref_text         = answer_data["ref_text"]
            if answer_data["next_question_id"]:
                next_qid = answer_data["next_question_id"]

        if is_correct:
            correct_value = choice["value"]
            if json_resp.get("NextQuestionId"):
                next_qid = json_resp["NextQuestionId"]
            break

        # Small delay between retry attempts
        if i < len(choices) - 1:
            time.sleep(0.4)

    if first_resp is None:
        return None

    return {
        "assessment_id":        assessment_id,
        "question_id":          question_id,
        "url":                  url,
        "quiz_title":           html_data["quiz_title"],
        "question_number":      html_data["question_number"],
        "questions_total":      html_data["questions_total"],
        "stem":                 html_data["stem"],
        "choices":              choices,
        "correct_value":        correct_value,          # value of correct radio button
        "correct_text":         next(                   # human-readable correct answer
            (c["text"] for c in choices if c["value"] == correct_value), ""
        ) if correct_value else "",
        "explanation":          explanation,
        "explanation_html":     explanation_html,       # raw HTML — preserved for re-extraction
        "ref_text":             ref_text,
        "next_question_id":     next_qid,
    }


# ─────────────────────────────────────────────────────────────────────
# MODE 1: EXPLORE
# ─────────────────────────────────────────────────────────────────────
def explore_mode(session: requests.Session):
    url = BASE_URL.format(assessment_id=FIRST_ASSESSMENT_ID, question_id=FIRST_QUESTION_ID)
    print(f"\n── EXPLORE MODE ──────────────────────────────────────────")
    print(f"URL: {url}")

    # GET
    html_data = get_question_html(session, url)
    if not html_data:
        print("ERROR: Could not fetch/parse question page.")
        return

    print(f"AUTH: OK")
    print(f"  Quiz:     {html_data['quiz_title']}")
    print(f"  Question: {html_data['question_number']} of {html_data['questions_total']}")
    print(f"  Choices:  {[(c['value'], c['text'][:30]) for c in html_data['choices']]}")
    print(f"  CSRF:     {'found' if html_data['csrf_token'] else 'NOT FOUND'}")

    # POST with first choice
    first_value = html_data["choices"][0]["value"]
    print(f"\nPOSTing answer value: {first_value} ({html_data['choices'][0]['text']})...")
    json_resp = post_answer(session, url, html_data, first_value)

    if json_resp is None:
        print("ERROR: POST failed — no JSON response")
        return

    # Dump everything
    with open(DUMP_FILE, "w", encoding="utf-8") as f:
        f.write(f"AAFP Explore Dump\nURL: {url}\n\n")
        f.write("── HTML DATA ──\n")
        html_copy = dict(html_data)
        html_copy.pop("csrf_token", None)
        f.write(json.dumps(html_copy, indent=2, ensure_ascii=False))
        f.write("\n\n── JSON RESPONSE (from POST) ──\n")
        f.write(json.dumps(json_resp, indent=2, ensure_ascii=False))

    print(f"\nDump saved → {DUMP_FILE}")
    print(f"\n── JSON RESPONSE FIELDS ──")
    for k, v in json_resp.items():
        val_str = str(v)[:200].replace("\n", " ")
        print(f"  {k}: {val_str}")

    answer_data = parse_answer_json(json_resp, html_data["choices"])
    print(f"\n── PARSED ──")
    print(f"  IsCorrect:           {json_resp.get('IsCorrect')}")
    print(f"  CorrectIndicators:   {repr(answer_data['correct_indicators'])}")
    print(f"  NextQuestionId:      {answer_data['next_question_id']}")
    print(f"  AllowRetry:          {answer_data['allow_retry']}")
    print(f"  ShowCorrect:         {answer_data['show_correct']}")
    print(f"  Explanation preview: {answer_data['explanation'][:200]}")
    print(f"  Ref text:            {answer_data['ref_text'][:150]}")


# ─────────────────────────────────────────────────────────────────────
# HELPER: Resolve first question ID via redirect
# ─────────────────────────────────────────────────────────────────────
def get_first_question_id(session: requests.Session, assessment_id: int) -> int | None:
    """
    GET /assessment/take/{aid}/c/ with redirects — server lands us on the
    current (first unanswered) question. Extract question ID from final URL.
    Falls back to scanning the response body for a /c/{id} pattern.
    """
    base_url = f"https://www.aafp.org/assessment/take/{assessment_id}/c/"
    try:
        resp = session.get(base_url, timeout=20, allow_redirects=True)
        # Check final URL first
        m = re.search(r"/c/(\d+)$", resp.url)
        if m:
            return int(m.group(1))
        m = re.search(r"/c/(\d+)", resp.url)
        if m:
            return int(m.group(1))
        # Fallback: scan HTML for question URL
        m = re.search(r"/assessment/take/\d+/c/(\d+)", resp.text)
        if m:
            return int(m.group(1))
    except Exception as e:
        print(f"    get_first_question_id({assessment_id}) error: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────
# MODE 2: DISCOVER
# ─────────────────────────────────────────────────────────────────────
def discover_mode(session: requests.Session):
    print(f"\n── DISCOVER MODE ─────────────────────────────────────────")
    print(f"Probing IDs {FIRST_ASSESSMENT_ID} → {FIRST_ASSESSMENT_ID + MAX_PROBE_IDS}\n")

    quiz_map = {}
    consecutive_misses = 0

    for aid in range(FIRST_ASSESSMENT_ID, FIRST_ASSESSMENT_ID + MAX_PROBE_IDS + 1):
        intro_url = INTRO_URL.format(assessment_id=aid)
        try:
            resp = session.get(intro_url, timeout=15, allow_redirects=True)
            if resp.status_code == 200 and "Board Review Questions" in resp.text:
                soup = BeautifulSoup(resp.text, "html.parser")
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else f"Assessment {aid}"

                # Find first question link on intro page
                first_q_id = None
                q_link = soup.find("a", href=re.compile(r"/assessment/take/\d+/c/(\d+)"))
                if q_link:
                    m = re.search(r"/c/(\d+)", q_link["href"])
                    if m:
                        first_q_id = int(m.group(1))

                quiz_map[str(aid)] = {"title": title, "first_question_id": first_q_id}
                print(f"  ✓ {aid}: {title}  (first Q: {first_q_id})")
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                if consecutive_misses % 10 == 0:
                    print(f"  ... {consecutive_misses} misses at ID {aid}")
                if consecutive_misses >= 30:
                    print(f"  30 consecutive misses — done at {aid}")
                    break
        except Exception as e:
            consecutive_misses += 1

        time.sleep(REQUEST_DELAY * 0.4)

    print(f"\nFound {len(quiz_map)} quiz sets")
    with open(QUIZ_MAP_FILE, "w") as f:
        json.dump(quiz_map, f, indent=2)
    print(f"Quiz map → {QUIZ_MAP_FILE}")
    return quiz_map


# ─────────────────────────────────────────────────────────────────────
# RESUME HELPER
# ─────────────────────────────────────────────────────────────────────
def load_existing_results(output_file: Path) -> tuple[list, set]:
    """
    Load existing staging results with corruption tolerance.

    Returns (records, scraped_assessment_ids):
      - Valid JSON    → parse normally, return all records
      - Truncated     → salvage all complete records before corruption point
      - Missing/empty → return empty list and empty set

    The salvage logic exploits the indent=2 format: every completed top-level
    object ends with a line "  }," (or "  }" for the last entry). The last
    such boundary before truncation marks the end of safe data.

    To override resume and start fresh: delete or rename the output file.
    """
    if not output_file.exists():
        return [], set()

    try:
        raw = output_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  Could not read {output_file.name}: {e}")
        return [], set()

    if not raw.strip():
        return [], set()

    # Try parsing as-is
    try:
        records = json.loads(raw)
        aids = {r["assessment_id"] for r in records}
        print(f"  Resuming: {len(records)} existing records across {len(aids)} quizzes")
        return records, aids
    except json.JSONDecodeError:
        pass

    # File truncated mid-write — salvage complete records.
    # With indent=2 each completed object ends with "\n  }," (non-last) in the array.
    # "\n  }," is 5 chars: \n(+0) space(+1) space(+2) }(+3) ,(+4)
    # We want text through the "}" at offset +3, then close the array.
    last_boundary = raw.rfind('\n  },')
    if last_boundary >= 0:
        salvaged_text = raw[:last_boundary + 4] + '\n]'
        try:
            records = json.loads(salvaged_text)
            aids = {r["assessment_id"] for r in records}
            print(f"  Salvaged {len(records)} records from truncated file ({len(aids)} quizzes complete)")
            print(f"  Last complete quiz: assessment {max(aids)} — resuming from next")
            return records, aids
        except json.JSONDecodeError as e:
            print(f"  Salvage parse failed ({e}) — starting fresh")

    print(f"  Existing file unrecoverable — starting fresh")
    return [], set()


# ─────────────────────────────────────────────────────────────────────
# MODE 3: SCRAPE
# ─────────────────────────────────────────────────────────────────────
def scrape_mode(session: requests.Session):
    print(f"\n── SCRAPE MODE ───────────────────────────────────────────")

    if QUIZ_MAP_FILE.exists():
        with open(QUIZ_MAP_FILE) as f:
            quiz_map = json.load(f)
        print(f"Loaded {len(quiz_map)} quizzes from quiz map")
    else:
        print("No quiz map — run --discover first. Using quiz 01 for testing.")
        quiz_map = {str(FIRST_ASSESSMENT_ID): {
            "title": "Board Review Questions 01",
            "first_question_id": FIRST_QUESTION_ID,
        }}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Resume: load any existing results (handles valid JSON and truncated files)
    print(f"\nChecking for existing output...")
    all_results, scraped_aids = load_existing_results(OUTPUT_FILE)
    if not scraped_aids:
        print(f"  Starting fresh")

    total_ok   = len(all_results)
    total_fail = 0

    for aid_str, info in quiz_map.items():
        aid       = int(aid_str)
        title     = info.get("title", f"Assessment {aid}")
        first_qid = info.get("first_question_id")

        # Skip quizzes already captured in a previous run
        if aid in scraped_aids:
            continue

        # Check known overrides first (prevents skipping touched questions)
        if aid in KNOWN_FIRST_QUESTIONS:
            first_qid = KNOWN_FIRST_QUESTIONS[aid]

        if not first_qid:
            # Formula: quiz question IDs are sequential, 10 per quiz,
            # anchored at quiz 01 (assessment 13882) → Q49733
            first_qid = FIRST_QUESTION_ID + (aid - FIRST_ASSESSMENT_ID) * QUESTIONS_PER_QUIZ
            # (no extra HTTP call needed — formula is deterministic)

        print(f"\n  Quiz {aid}: {title}")
        current_qid = first_qid

        for q_num in range(1, QUESTIONS_PER_QUIZ + 1):
            result = fetch_question(session, aid, current_qid)

            if result is None:
                print(f"    [{q_num:02d}/10] Q{current_qid} — FAILED")
                total_fail += 1
                current_qid += 1  # fallback: try next sequential ID
                continue

            all_results.append(result)
            total_ok += 1

            c_flag = "✓" if result["correct_value"] else "✗"
            r_flag = "✓" if result["ref_text"] else "✗"
            print(f"    [{q_num:02d}/10] Q{current_qid} correct:{c_flag} ref:{r_flag}  "
                  f"next:{result['next_question_id']}  {result['stem'][:50]}...")

            # Follow NextQuestionId from server (authoritative)
            if result["next_question_id"]:
                current_qid = result["next_question_id"]
            else:
                # End of quiz
                break

            time.sleep(REQUEST_DELAY)

        # Save incrementally after each quiz
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n══ SCRAPE COMPLETE ═══════════════════════════════════════")
    print(f"  Questions scraped:       {total_ok}")
    print(f"  Failed:                  {total_fail}")
    print(f"  correct_value resolved:  {sum(1 for r in all_results if r['correct_value'])}/{total_ok}")
    print(f"  ref_text found:          {sum(1 for r in all_results if r['ref_text'])}/{total_ok}")
    print(f"  correct first try:       {sum(1 for r in all_results if r.get('is_correct_first_try'))}/{total_ok}")
    print(f"  Output → {OUTPUT_FILE}")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("--explore", "--discover", "--scrape"):
        print("Usage:")
        print("  python aafp_brq_scraper.py --explore    ← start here")
        print("  python aafp_brq_scraper.py --discover   ← find all quiz IDs")
        print("  python aafp_brq_scraper.py --scrape     ← full extraction")
        sys.exit(0)

    print("Building authenticated session...")
    session = make_session()

    if sys.argv[1] == "--explore":
        explore_mode(session)
    elif sys.argv[1] == "--discover":
        discover_mode(session)
    elif sys.argv[1] == "--scrape":
        scrape_mode(session)
