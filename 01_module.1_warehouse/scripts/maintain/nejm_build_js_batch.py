"""Generate JS code for one batch of NEJM downloads.

Reads `_nejm_with_dois.json` (must include `doi` per entry).
Args:
  --start N    Start index (0-based)
  --count N    Number of articles to include in this batch (default 10)
Outputs the JS code to execute in the NEJM tab.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PENDING = SCRIPT_DIR / "_nejm_with_dois.json"


def normalize_author(author: str) -> str:
    a = re.split(r"[\s,]+", author.strip())[0]
    a = re.sub(r"[^A-Za-z\-']", "", a)
    if not a:
        return "Unknown"
    return a[0].upper() + a[1:]


def codon(author: str, year: str, article_id: str) -> str:
    return f"{normalize_author(author)}_{year}#@#{article_id}@#@.pdf"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--count", type=int, default=10)
    args = ap.parse_args()

    entries = json.loads(PENDING.read_text(encoding="utf-8"))
    # Filter to entries with DOIs
    entries = [e for e in entries if e.get("doi")]
    batch = entries[args.start : args.start + args.count]
    if not batch:
        print("// No entries in this batch", file=sys.stderr)
        return 1
    jobs = []
    for e in batch:
        fname = codon(e["author"], e["year"], e["article_id"])
        jobs.append({
            "doi": "/doi/pdf/" + e["doi"],
            "fname": fname,
            "article_id": e["article_id"],
        })
    js = f"""(async () => {{
  const jobs = {json.dumps(jobs)};
  const results = [];
  for (const j of jobs) {{
    try {{
      const r = await fetch(j.doi, {{credentials: 'include'}});
      if (!r.ok) {{ results.push({{id: j.article_id, error: 'http ' + r.status}}); continue; }}
      const buf = await r.arrayBuffer();
      if (buf.byteLength < 5000) {{ results.push({{id: j.article_id, error: 'too small ' + buf.byteLength}}); continue; }}
      const blob = new Blob([buf], {{type:'application/pdf'}});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = j.fname; a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {{ try {{ document.body.removeChild(a); URL.revokeObjectURL(url); }} catch(e){{}} }}, 2000);
      results.push({{id: j.article_id, size: buf.byteLength, fname: j.fname}});
      await new Promise(r => setTimeout(r, 800));
    }} catch (e) {{
      results.push({{id: j.article_id, error: e.toString()}});
    }}
  }}
  return results;
}})()"""
    print(js)
    print(f"// batch {args.start}..{args.start + len(batch) - 1} ({len(batch)} jobs)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
