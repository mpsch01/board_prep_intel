"""Build a single JS script to paste into Chrome DevTools console on nejm.org.

Run in DevTools console (F12 → Console tab) on https://www.nejm.org/.
Downloads all 75 remaining NEJM PDFs to your Downloads folder, with codon filenames.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PENDING = SCRIPT_DIR / "_nejm_with_dois.json"
OUTPUT = SCRIPT_DIR / "_nejm_console_script.txt"

# Already done
SKIP = {"ART-0082"}


def normalize_author(author: str) -> str:
    a = re.split(r"[\s,]+", author.strip())[0]
    a = re.sub(r"[^A-Za-z\-']", "", a)
    if not a:
        return "Unknown"
    return a[0].upper() + a[1:]


def codon(author: str, year: str, article_id: str) -> str:
    return f"{normalize_author(author)}_{year}#@#{article_id}@#@.pdf"


def main():
    entries = json.loads(PENDING.read_text(encoding="utf-8"))
    entries = [e for e in entries if e.get("doi") and e["article_id"] not in SKIP]
    jobs = [{
        "doi": "/doi/pdf/" + e["doi"],
        "fname": codon(e["author"], e["year"], e["article_id"]),
        "id": e["article_id"],
    } for e in entries]
    print(f"// {len(jobs)} jobs")
    js = (
        "(async () => {\n"
        f"  const jobs = {json.dumps(jobs)};\n"
        "  console.log('NEJM harvest: ' + jobs.length + ' articles');\n"
        "  const results = [];\n"
        "  for (let i = 0; i < jobs.length; i++) {\n"
        "    const j = jobs[i];\n"
        "    try {\n"
        "      const r = await fetch(j.doi, {credentials: 'include'});\n"
        "      if (!r.ok) { console.warn(`[${i+1}/${jobs.length}] ${j.id}: HTTP ${r.status}`); results.push({id:j.id, error:'http '+r.status}); continue; }\n"
        "      const buf = await r.arrayBuffer();\n"
        "      if (buf.byteLength < 5000) { console.warn(`[${i+1}/${jobs.length}] ${j.id}: too small ${buf.byteLength}`); results.push({id:j.id, error:'too small'}); continue; }\n"
        "      const blob = new Blob([buf], {type:'application/pdf'});\n"
        "      const url = URL.createObjectURL(blob);\n"
        "      const a = document.createElement('a');\n"
        "      a.href = url; a.download = j.fname; a.style.display='none';\n"
        "      document.body.appendChild(a);\n"
        "      a.click();\n"
        "      console.log(`[${i+1}/${jobs.length}] ${j.id} -> ${j.fname} (${buf.byteLength} bytes)`);\n"
        "      results.push({id:j.id, size:buf.byteLength, fname:j.fname});\n"
        "      await new Promise(r => setTimeout(r, 1500));\n"
        "      try { document.body.removeChild(a); URL.revokeObjectURL(url); } catch(e){}\n"
        "    } catch (e) {\n"
        "      console.error(`[${i+1}/${jobs.length}] ${j.id}: ` + e.toString());\n"
        "      results.push({id:j.id, error:e.toString()});\n"
        "    }\n"
        "  }\n"
        "  const ok = results.filter(r => !r.error).length;\n"
        "  const fail = results.filter(r => r.error).length;\n"
        "  console.log(`DONE: ${ok} ok, ${fail} failed`);\n"
        "  return {ok, fail, results};\n"
        "})()"
    )
    OUTPUT.write_text(js, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Length: {len(js)} chars")
    return 0


if __name__ == "__main__":
    main()
