"""
prompt_builder.py -- Real Anthropic API client for guideline extraction.

Provides:
  - llm_generate(prompt, system, max_tokens, json_mode) -> str
  - llm_screen(text_chunk) -> dict  (used by screening classifier)
  - llm_extract(document_text, document_type) -> dict (used by engines)
  - extract_metadata(text) -> dict  (title, year, organization)
  - llm_extract_chunked(full_text, document_type) -> dict  (for large docs)

API key resolution order:
  1. ANTHROPIC_API_KEY environment variable
  2. config.json at project root: {"ANTHROPIC_API_KEY": "sk-ant-..."}
"""

from __future__ import annotations
import json
import os
import re
import concurrent.futures
import anthropic

MODEL = "claude-sonnet-4-20250514"
_client = None  # lazy-initialized

# Chunking parameters -- tuned for large society guidelines (500k-800k chars)
LARGE_DOC_THRESHOLD = 15000   # docs above this get chunked
CHUNK_SIZE          = 25000   # chars per chunk
CHUNK_OVERLAP       = 2500    # overlap between chunks
MAX_CHUNKS          = 12      # cap -- covers ~272k chars max


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        config_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "config.json")
        )
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f)
            api_key = cfg.get("ANTHROPIC_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found.\n"
            "Set it as an environment variable OR create config.json at the project root:\n"
            '  {"ANTHROPIC_API_KEY": "sk-ant-..."}'
        )

    _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ─────────────────────────────────────────────
# Core API wrapper
# ─────────────────────────────────────────────

def llm_generate(
    prompt: str,
    system: str = "You are a clinical informatics assistant. Be precise and concise.",
    max_tokens: int = 1000,
    json_mode: bool = False,
) -> str:
    if json_mode:
        system = system + "\nRESPOND ONLY WITH VALID JSON. No markdown, no preamble, no trailing text."

    message = _get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def llm_generate_json(prompt: str, system: str, max_tokens: int = 1000) -> dict:
    raw = llm_generate(prompt, system=system, max_tokens=max_tokens, json_mode=True)
    # Strip markdown fences
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    # Strip any preamble text before the first { or [
    # Handles cases where the LLM prepends explanation text before JSON
    first_brace = min(
        (clean.find("{") if clean.find("{") != -1 else len(clean)),
        (clean.find("[") if clean.find("[") != -1 else len(clean)),
    )
    if first_brace > 0:
        clean = clean[first_brace:]
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON response: {e}\n\nRaw response:\n{raw[:500]}")


# ─────────────────────────────────────────────
# Metadata extraction (title, year, org)
# ─────────────────────────────────────────────

METADATA_SYSTEM = """You are a clinical document metadata extractor.
Extract bibliographic metadata from the provided text.
RESPOND ONLY WITH VALID JSON. No markdown, no preamble."""

METADATA_PROMPT = """Extract metadata from the beginning of this clinical document.

Return a JSON object with:
- "title": full document title (string, empty string if not found)
- "organization": publishing organization or journal (e.g. "IDSA", "USPSTF", "American Family Physician") (string, empty if not found)
- "publication_year": year as integer (null if not found)
- "version_number": version or edition if stated (string, empty if not found)
- "doi": DOI if present (string, empty if not found)

DOCUMENT START (first 2000 chars):
{text}
"""

def extract_metadata(text: str) -> dict:
    """Extract title, org, year, version, doi from document text."""
    prompt = METADATA_PROMPT.format(text=text[:2000])
    try:
        result = llm_generate_json(prompt, system=METADATA_SYSTEM, max_tokens=300)
        return {
            "title": result.get("title", ""),
            "organization": result.get("organization", ""),
            "publication_year": result.get("publication_year", None),
            "version_number": result.get("version_number", ""),
            "doi": result.get("doi", ""),
        }
    except Exception:
        return {
            "title": "", "organization": "", "publication_year": None,
            "version_number": "", "doi": "",
        }


# ─────────────────────────────────────────────
# Screening prompt
# ─────────────────────────────────────────────

SCREENING_SYSTEM = """You are a clinical document classifier.
Your job is to classify clinical documents by type based on a text excerpt.
RESPOND ONLY WITH VALID JSON. No markdown, no preamble."""

SCREENING_PROMPT_TEMPLATE = """Classify the following clinical document excerpt into exactly one document type.

Use these strict definitions to choose:

- "acute_protocol": PRIMARY focus is management of an acute, time-sensitive, or emergency condition.
  Key signals: treatment windows, inpatient stabilization, emergency medications, disposition decisions,
  antibiotic selection for active infection, severity triage. Examples: influenza treatment, croup
  management, oncologic emergencies, bronchiolitis, diverticulitis, rhinosinusitis.
  USE THIS even if the document also covers diagnosis -- if management/treatment is the dominant content.

- "chronic_guideline": PRIMARY focus is long-term management of a chronic condition.
  Key signals: stepwise therapy, medication titration, lifestyle modification, long-term monitoring,
  exacerbation prevention, risk stratification over time. Examples: COPD, hypertension, diabetes,
  heart failure, coronary artery disease, peripheral artery disease, dyslipidemia.
  USE THIS even if the document also covers diagnosis.

- "preventive_guideline": PRIMARY focus is screening, prevention, or health maintenance in
  asymptomatic or at-risk populations.
  Key signals: screening intervals, age/risk-based eligibility, USPSTF grades (A/B/C/D/I),
  chemoprophylaxis, vaccination, primary prevention, well-child visits.
  Examples: lung cancer screening, AAA screening, aspirin for CVD prevention, statins for
  primary prevention, Bright Futures health supervision.

- "diagnostic_guideline": PRIMARY focus is HOW TO DIAGNOSE -- workup algorithms, test selection,
  result interpretation, imaging decision trees, biopsy thresholds, or managing incidentally
  discovered findings. Treatment is secondary or absent.
  Key signals: diagnostic criteria, test thresholds, imaging interpretation, classification systems,
  FNA indications, spirometry interpretation, capacity evaluation tools.
  Examples: thyroid nodule workup, incidentalomas, spirometry interpretation, TB diagnosis,
  decision-making capacity, chest pain evaluation algorithm, perioperative cardiac risk assessment.
  DO NOT USE THIS for documents where treatment/management is clearly the primary content.

- "rct": A primary research article reporting results of a randomized controlled trial.
  Key signals: METHODS section, randomization, trial arms, hazard ratios, confidence intervals,
  p-values, Kaplan-Meier curves, intention-to-treat analysis, NEJM/Lancet/JAMA article format
  with abstract, introduction, methods, results, discussion.
  This is NOT a clinical guideline -- it is original research.

- "unknown": Cannot confidently classify with the above definitions.

Return a JSON object with:
- "document_type": one of the six types above
- "confidence": float 0.0 to 1.0
- "signals": list of up to 5 short text phrases from the excerpt that drove your classification
- "body_systems": list of body systems involved (e.g. ["respiratory", "cardiovascular"])
- "numeric_threshold_present": boolean -- true if specific numeric thresholds appear

DOCUMENT EXCERPT:
{text_chunk}
"""

def llm_screen(text_chunk: str) -> dict:
    prompt = SCREENING_PROMPT_TEMPLATE.format(text_chunk=text_chunk[:3000])
    return llm_generate_json(prompt, system=SCREENING_SYSTEM, max_tokens=400)


# ─────────────────────────────────────────────
# Extraction prompts
# ─────────────────────────────────────────────

CHRONIC_EXTRACT_SYSTEM = """You are a clinical guideline extraction engine specialized in chronic disease management.
Extract structured information precisely from the provided clinical document.
RESPOND ONLY WITH VALID JSON. No markdown, no preamble, no explanation.

QUALITY REQUIREMENTS — CALIBRATION v1 (2026-03-05):
For EVERY recommendation, you MUST populate the 'evidence_level' field.
Use the guideline's own evidence coding if present. If the guideline uses letter codes, expand them:
"A" or "Grade A" -> "Grade A (strong evidence, RCT-based)"
"B" or "Grade B" -> "Grade B (moderate evidence, observational)"
"C" or "Grade C" -> "Grade C (expert consensus)"
"B-R" -> "Grade B-R (moderate, randomized)"
"C-EO" -> "Grade C-EO (expert opinion)"
If the guideline has no grading system, infer from study design:
  RCT-supported -> "Grade A (RCT-supported)"
  Observational/cohort data -> "Grade B (observational evidence)"
  Expert consensus/panel -> "Grade C (expert consensus)"
  Single case series -> "Grade C (case series/expert opinion)"
Never leave evidence_level as an empty string or single letter."""

CHRONIC_EXTRACT_PROMPT = """Extract the following from this chronic disease clinical guideline.

Return a JSON object with these fields:
- "summary": 2-3 sentence clinical summary
- "population": object with fields: age_criteria, risk_criteria, disease_definition, exclusions, severity_staging
- "key_thresholds": array of objects with: parameter, value, unit, context
- "recommendations": array of objects with: recommendation (string), strength (e.g. "Strong", "Conditional"), evidence_level (e.g. "A", "B", "C"), notes
- "medications": array of objects with: drug, dose, indication, class
- "red_flags": array of strings -- clinical warning signs requiring escalation
- "follow_up": string -- recommended monitoring/follow-up schedule
- "escalation_path": string -- when/how to escalate care

DOCUMENT TEXT:
{document_text}
"""

ACUTE_EXTRACT_SYSTEM = """You are a clinical guideline extraction engine specialized in acute and emergency protocols.
Extract structured actionable information from the provided clinical document.
RESPOND ONLY WITH VALID JSON. No markdown, no preamble, no explanation.

QUALITY REQUIREMENTS — CALIBRATION v1 (2026-03-05):
For EVERY recommendation, you MUST populate the 'strength' field.
Use the guideline's own grading (e.g., "Strong", "Conditional", "Class I", "Grade A"). If not stated, infer from language: "should"/"recommend"/"is indicated" -> "Strong", "may"/"consider"/"is reasonable" -> "Conditional", "insufficient evidence" -> "Insufficient Evidence". Never leave strength empty.
For EVERY recommendation, you MUST populate the 'evidence_level' field.
Use the guideline's own coding if present. If the guideline uses letter codes, expand them:
"A" -> "Grade A (strong evidence, RCT-based)"
"B" -> "Grade B (moderate evidence, observational)"
"C" -> "Grade C (expert consensus)"
"B-R" -> "Grade B-R (moderate, randomized)"
"C-EO" -> "Grade C-EO (expert opinion)"
If no grading system: RCT-supported -> "Grade A (RCT-supported)", Observational -> "Grade B (observational)", Expert consensus -> "Grade C (expert consensus)".
Never leave evidence_level as an empty string or single letter.
For EVERY threshold entry, you MUST populate the 'unit' field using standard clinical notation:
Blood pressure: mmHg | Lab values: mg/dL, mmol/L, mEq/L, g/dL, IU/L | Weight: kg, lbs | Time: days, weeks, months, years | Scores: "points" or "score" | Percentages: "%".
Never leave unit blank if a numeric threshold is given."""

ACUTE_EXTRACT_PROMPT = """Extract the following from this acute/emergency clinical protocol.

Return a JSON object with these fields:
- "summary": 2-3 sentence clinical summary of the emergency/acute condition
- "population": object with fields: age_criteria, risk_criteria, disease_definition, exclusions, severity_staging
- "key_thresholds": array of objects with: parameter, value, unit, context (e.g. vital sign cutoffs, lab values)
- "recommendations": array of objects with: recommendation, strength, evidence_level, notes
- "medications": array of objects with: drug, dose, indication, class
- "red_flags": array of strings -- immediate danger signs
- "follow_up": string -- post-stabilization monitoring
- "escalation_path": string -- when to escalate (ICU, specialist consult, transfer, etc.)

DOCUMENT TEXT:
{document_text}
"""

PREVENTIVE_EXTRACT_SYSTEM = """You are a clinical guideline extraction engine specialized in preventive medicine and screening.
Extract structured screening and prevention information precisely.
RESPOND ONLY WITH VALID JSON. No markdown, no preamble, no explanation.

QUALITY REQUIREMENTS — CALIBRATION v1 (2026-03-05):
For EVERY threshold entry, you MUST populate the 'unit' field using standard clinical notation:
Blood pressure: mmHg | Lab values: mg/dL, mmol/L, mEq/L, g/dL, IU/L | Age thresholds: "years" | Screening intervals: "years" or "months" | Pack-years: "pack-years" | Scores: "points" or "score" | Percentages: "%".
Never leave unit blank if a numeric threshold is given."""

PREVENTIVE_EXTRACT_PROMPT = """Extract the following from this preventive medicine / screening guideline.

Return a JSON object with these fields:
- "summary": 2-3 sentence summary of the preventive intervention or screening recommendation
- "population": object with fields: age_criteria, risk_criteria, disease_definition, exclusions, severity_staging
- "key_thresholds": array of objects with: parameter, value, unit, context (e.g. screening ages, intervals, cutoff scores)
- "recommendations": array of objects with: recommendation, strength, evidence_level, notes
- "medications": array of objects with: drug, dose, indication, class (vaccines, chemoprophylaxis, etc.)
- "red_flags": array of strings -- high-risk findings requiring immediate follow-up
- "follow_up": string -- screening interval or follow-up schedule
- "escalation_path": string -- what to do with a positive screen

DOCUMENT TEXT:
{document_text}
"""

DIAGNOSTIC_EXTRACT_SYSTEM = """You are a clinical guideline extraction engine specialized in diagnostic workup and test interpretation.
Extract structured diagnostic information precisely from the provided clinical document.
Focus on: diagnostic criteria, test thresholds, workup algorithms, result interpretation, and referral indications.
RESPOND ONLY WITH VALID JSON. No markdown, no preamble, no explanation.

QUALITY REQUIREMENTS — CALIBRATION v1 (2026-03-05):
For EVERY threshold entry, you MUST populate the 'unit' field using standard clinical notation:
Lab values: mg/dL, mmol/L, mEq/L, g/dL, IU/L, mIU/L | Size measurements: mm, cm | Scores: "points" or "score" | Age thresholds: "years" | Percentages: "%" | Time windows: "days", "weeks", "months".
Never leave unit blank if a numeric threshold is given."""

DIAGNOSTIC_EXTRACT_PROMPT = """Extract the following from this diagnostic / workup clinical guideline.

Return a JSON object with these fields:
- "summary": 2-3 sentence clinical summary describing what condition is being diagnosed and the primary diagnostic approach
- "population": object with fields: age_criteria, risk_criteria, disease_definition, exclusions, severity_staging
- "key_thresholds": array of objects with: parameter, value, unit, context
  (Focus on diagnostic cutoffs: test values that define positive/negative results, size thresholds, score cutoffs)
- "recommendations": array of objects with: recommendation, strength, evidence_level, notes
  (Focus on: when to test, which test to use, how to interpret results, when to refer)
- "medications": array of objects with: drug, dose, indication, class
  (Include only if relevant, e.g. contrast agents, sedation for procedures, treatment after diagnosis)
- "red_flags": array of strings -- findings requiring urgent escalation or immediate intervention
- "follow_up": string -- recommended surveillance / repeat testing schedule
- "escalation_path": string -- when to refer, when to biopsy, when to treat, when to involve subspecialty

DOCUMENT TEXT:
{document_text}
"""

RCT_EXTRACT_SYSTEM = """You are a clinical research extraction engine specialized in randomized controlled trials.
Extract structured trial information precisely from the provided research article.
RESPOND ONLY WITH VALID JSON. No markdown, no preamble, no explanation."""

RCT_EXTRACT_PROMPT = """Extract the following from this randomized controlled trial article.

Return a JSON object with these fields:
- "summary": 2-3 sentence summary of the trial question, intervention, and primary finding
- "population": object with: age_criteria, risk_criteria, disease_definition, exclusions, severity_staging
  (map to: trial inclusion/exclusion criteria and patient population)
- "key_thresholds": array of objects with: parameter, value, unit, context
  (Include: primary endpoint values, HR/RR/OR with CI, p-values, NNT/NNH, baseline characteristics)
- "recommendations": array of objects with: recommendation, strength, evidence_level, notes
  (Map to: trial conclusions, clinical implications, subgroup findings)
- "medications": array of objects with: drug, dose, indication, class
  (Include ALL trial arms -- intervention AND comparator/placebo)
- "red_flags": array of strings -- safety signals, adverse events, reasons for discontinuation
- "follow_up": string -- trial follow-up duration and outcome assessment schedule
- "escalation_path": string -- clinical applicability, generalizability, next steps from authors

DOCUMENT TEXT:
{document_text}
"""

EXTRACT_PROMPTS = {
    "chronic_guideline":    (CHRONIC_EXTRACT_SYSTEM,    CHRONIC_EXTRACT_PROMPT),
    "acute_protocol":       (ACUTE_EXTRACT_SYSTEM,      ACUTE_EXTRACT_PROMPT),
    "preventive_guideline": (PREVENTIVE_EXTRACT_SYSTEM, PREVENTIVE_EXTRACT_PROMPT),
    "diagnostic_guideline": (DIAGNOSTIC_EXTRACT_SYSTEM, DIAGNOSTIC_EXTRACT_PROMPT),
    "rct":                  (RCT_EXTRACT_SYSTEM,        RCT_EXTRACT_PROMPT),
    "unknown":              (CHRONIC_EXTRACT_SYSTEM,    CHRONIC_EXTRACT_PROMPT),
}


# ─────────────────────────────────────────────
# Extraction -- standard and chunked
# ─────────────────────────────────────────────

def _load_supplements(document_type: str) -> str:
    """Load prompt supplements from oneclick/prompt_supplements.json if it exists."""
    supplements_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "oneclick", "prompt_supplements.json"
    )
    if not os.path.exists(supplements_path):
        return ""
    try:
        with open(supplements_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return ""
    lines = []
    for s in data.get("supplements", []):
        targets = s.get("target_engines", [])
        if "all" in targets or document_type in targets:
            lines.append(s["instruction"])
    if lines:
        return "\n\nADDITIONAL EXTRACTION GUIDANCE (from calibration):\n" + "\n".join(f"- {l}" for l in lines)
    return ""


def llm_extract(document_text: str, document_type: str, max_tokens: int = 3000) -> dict:
    """
    Run extraction on a document. Automatically uses chunked extraction
    for documents exceeding LARGE_DOC_THRESHOLD characters.
    """
    if len(document_text) > LARGE_DOC_THRESHOLD:
        return llm_extract_chunked(document_text, document_type, max_tokens)
    system, prompt_template = EXTRACT_PROMPTS.get(document_type, EXTRACT_PROMPTS["unknown"])
    system += _load_supplements(document_type)
    prompt = prompt_template.format(document_text=document_text)
    return llm_generate_json(prompt, system=system, max_tokens=max_tokens)


def llm_extract_chunked(full_text: str, document_type: str, max_tokens: int = 3000) -> dict:
    """
    Extract from large documents by splitting into overlapping chunks,
    processing with rate-aware parallelism, then merging results.

    Rate limit: 30,000 input tokens/min on free tier.
    Each chunk ~25k chars = ~6,250 tokens + ~500 prompt overhead = ~6,750 tokens.
    Safe concurrency: 2 workers with staggered start delays to stay under 30k TPM.
    Exponential backoff on 429s (2s, 4s, 8s, 16s) before giving up.
    """
    import time
    system, prompt_template = EXTRACT_PROMPTS.get(document_type, EXTRACT_PROMPTS["unknown"])
    system += _load_supplements(document_type)
    step = CHUNK_SIZE - CHUNK_OVERLAP

    chunks = []
    pos = 0
    while pos < len(full_text) and len(chunks) < MAX_CHUNKS:
        chunks.append(full_text[pos: pos + CHUNK_SIZE])
        pos += step

    total = len(chunks)

    def process_chunk(args):
        i, chunk, start_delay = args
        if start_delay > 0:
            time.sleep(start_delay)
        prompt = prompt_template.format(document_text=chunk)
        backoff = 2
        for attempt in range(4):
            try:
                result = llm_generate_json(prompt, system=system, max_tokens=max_tokens)
                recs   = len(result.get("recommendations", []))
                thresh = len(result.get("key_thresholds", []))
                print(f"    [chunk {i+1}/{total}] recs={recs} thresh={thresh}")
                return (i, result)
            except Exception as e:
                if "429" in str(e) and attempt < 3:
                    print(f"    [chunk {i+1}/{total}] rate limited, retry in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    print(f"    [chunk {i+1}/{total}] FAILED: {e}")
                    return (i, None)
        return (i, None)

    # Stagger chunk start times: 2 workers, each pair offset by 5s
    # This keeps concurrent token consumption under 30k TPM
    STAGGER_SEC = 5
    chunk_args = [(i, chunk, (i // 2) * STAGGER_SEC) for i, chunk in enumerate(chunks)]

    chunk_results_raw = [None] * total
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_chunk, args): args[0]
                   for args in chunk_args}
        for future in concurrent.futures.as_completed(futures):
            i, result = future.result()
            chunk_results_raw[i] = result

    chunk_results = [r for r in chunk_results_raw if r is not None]

    if not chunk_results:
        raise ValueError("All chunks failed extraction")
    return _merge_chunk_results(chunk_results)


def _merge_chunk_results(results: list[dict]) -> dict:
    """
    Merge multiple chunk extraction results into one unified output.
    - summary, population, follow_up, escalation_path: take from first non-empty chunk
    - recommendations, key_thresholds, medications, red_flags: union, deduplicated by text
    """
    merged = {
        "summary": "",
        "population": {},
        "key_thresholds": [],
        "recommendations": [],
        "medications": [],
        "red_flags": [],
        "follow_up": "",
        "escalation_path": "",
        "_chunked_extraction": True,
        "_chunks_merged": len(results),
    }

    # Scalar fields: first non-empty wins
    for r in results:
        if not merged["summary"] and r.get("summary"):
            merged["summary"] = r["summary"]
        if not merged["population"] and r.get("population"):
            merged["population"] = r["population"]
        if not merged["follow_up"] and r.get("follow_up"):
            merged["follow_up"] = r["follow_up"]
        if not merged["escalation_path"] and r.get("escalation_path"):
            merged["escalation_path"] = r["escalation_path"]

    # List fields: deduplicate by first 60 chars of primary text field
    def _dedup(existing: list, new_items: list, key: str) -> list:
        seen = {item.get(key, "")[:60].lower() for item in existing}
        for item in new_items:
            sig = item.get(key, "")[:60].lower()
            if sig and sig not in seen:
                existing.append(item)
                seen.add(sig)
        return existing

    for r in results:
        _dedup(merged["recommendations"], r.get("recommendations", []), "recommendation")
        _dedup(merged["key_thresholds"], r.get("key_thresholds", []), "parameter")
        _dedup(merged["medications"], r.get("medications", []), "drug")
        # red_flags are plain strings
        existing_flags = {f[:60].lower() for f in merged["red_flags"]}
        for flag in r.get("red_flags", []):
            if flag[:60].lower() not in existing_flags:
                merged["red_flags"].append(flag)
                existing_flags.add(flag[:60].lower())

    return merged
