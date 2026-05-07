"""Look up DOIs for NEJM articles via Crossref API.

Reads `_nejm_pending.json` (article_id, author, year, title, tier).
Queries Crossref by title+author+year, filters for NEJM.
Writes `_nejm_with_dois.json` with DOI added (when found).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from curl_cffi import requests

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT = SCRIPT_DIR / "_nejm_pending.json"
OUTPUT = SCRIPT_DIR / "_nejm_with_dois.json"


def query_crossref(title: str, author: str, year: str) -> str | None:
    """Returns DOI for the best NEJM match, or None."""
    if not title:
        return None
    # Crossref search
    params = {
        "query.title": title[:200],
        "rows": "10",
    }
    if author:
        params["query.author"] = author[:50]
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"https://api.crossref.org/works?{qs}"
    try:
        r = requests.get(url, impersonate="chrome110", timeout=20,
                         headers={"User-Agent": "ITE-Intelligence-PDFFetch (mailto:mpsch@example.com)"})
    except Exception as e:
        return None
    if r.status_code != 200:
        return None
    data = r.json()
    items = data.get("message", {}).get("items", [])
    target_year = year if year else None
    target_title = re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()
    best = None
    best_score = 0
    for item in items:
        # Filter for NEJM: DOI starts with 10.1056 OR container-title contains "New England Journal"
        doi = item.get("DOI", "")
        ct = " ".join(item.get("container-title", [])).lower()
        is_nejm = doi.startswith("10.1056/") or "new england journal" in ct
        if not is_nejm:
            continue
        cand_title = " ".join(item.get("title", []))
        cand_norm = re.sub(r"[^a-z0-9 ]", "", cand_title.lower()).strip()
        target_words = set(target_title.split())
        cand_words = set(cand_norm.split())
        if not target_words:
            continue
        overlap = len(target_words & cand_words) / len(target_words)
        if overlap < 0.4:
            continue
        cand_year = None
        for y in (item.get("issued") or {}).get("date-parts", []):
            if y:
                cand_year = str(y[0])
                break
        if target_year and cand_year and cand_year != target_year:
            # Year mismatch — penalize but don't reject
            score = overlap - 0.2
        else:
            score = overlap + (0.3 if cand_year == target_year else 0)
        if score > best_score:
            best_score = score
            best = doi
    return best


def main() -> int:
    if not INPUT.exists():
        print(f"Missing {INPUT}")
        return 1
    pending = json.loads(INPUT.read_text(encoding="utf-8"))
    out = []
    found = 0
    for i, entry in enumerate(pending):
        if entry.get("doi"):
            out.append(entry)
            found += 1
            continue
        doi = query_crossref(entry["title"], entry.get("author") or "", entry.get("year") or "")
        entry["doi"] = doi
        out.append(entry)
        if doi:
            found += 1
            print(f"[{i+1:3d}/{len(pending)}] {entry['article_id']} -> {doi}")
        else:
            print(f"[{i+1:3d}/{len(pending)}] {entry['article_id']} -> (no match)")
        time.sleep(0.5)  # Polite to Crossref
        # Save incrementally every 10
        if (i+1) % 10 == 0:
            OUTPUT.write_text(json.dumps(out + pending[i+1:], indent=2), encoding="utf-8")
    OUTPUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSummary: {found}/{len(pending)} have DOIs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
