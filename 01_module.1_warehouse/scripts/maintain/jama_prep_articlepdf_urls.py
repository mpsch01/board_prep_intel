"""Parse jama_pending.json → emit list of (article_id, articlepdf_url, author, year, tier).

The articlepdf URL pattern works with arbitrary slug (verified):
  https://jamanetwork.com/journals/{JOURNAL}/articlepdf/{ARTICLE_ID}/x.pdf
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

SCRIPT_DIR = Path(__file__).resolve().parent
JAMA_PENDING = SCRIPT_DIR / "jama_pending.json"
OUTPUT = SCRIPT_DIR / "_jama_articlepdf_urls.json"


def parse_url(url: str) -> tuple[str, str] | None:
    """Returns (journal_segment, article_id) or None."""
    p = urlparse(url)
    parts = [x for x in p.path.split("/") if x]
    # Expected: journals / {journal} / {article-abstract|fullarticle} / {id}
    if len(parts) >= 4 and parts[0] == "journals":
        journal = parts[1]
        # URL-decode before stripping (handles %C2%A0 NBSP etc.)
        article_id = unquote(parts[3])
        article_id = re.sub(r"[^0-9]", "", article_id)
        return journal, article_id
    return None


def main() -> int:
    if not JAMA_PENDING.exists():
        print(f"Missing {JAMA_PENDING}")
        return 1
    pending = json.loads(JAMA_PENDING.read_text(encoding="utf-8"))
    out = []
    for entry in pending:
        parsed = parse_url(entry["url"])
        if not parsed:
            print(f"SKIP {entry['article_id']}: cannot parse {entry['url']}")
            continue
        journal, article_id = parsed
        articlepdf_url = f"https://jamanetwork.com/journals/{journal}/articlepdf/{article_id}/x.pdf"
        out.append({
            "article_id": entry["article_id"],
            "tier": entry["tier"],
            "author": entry["author"],
            "year": entry["year"],
            "articlepdf_url": articlepdf_url,
            "title": entry.get("title", ""),
        })
    OUTPUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(out)} entries to {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
