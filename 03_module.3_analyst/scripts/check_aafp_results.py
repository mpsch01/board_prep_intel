"""
check_aafp_results.py
======================
Reads claude_classifications.json (AAFP batch results), prints routing summary,
renames file to aafp_classifications.json, and shows error details.
"""
import json, shutil
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "03_module.3_analyst" / "outputs" / "body_system_labels"

src  = OUTPUT_DIR / "claude_classifications.json"
dest = OUTPUT_DIR / "aafp_classifications.json"

with open(src, encoding="utf-8") as f:
    data = json.load(f)

print(f"Total classified: {data['total_classified']}")
print(f"Errors:           {data.get('errors', 0)}")
print(f"Routing:")
for route, n in sorted(data.get("routing_summary", {}).items()):
    pct = 100 * n // data["total_classified"] if data["total_classified"] else 0
    print(f"  {route:<15} {n:4d}  ({pct}%)")

print()
print("Top proposed categories:")
from collections import Counter
cats = Counter(r["body_system_proposed"] for r in data["results"])
for cat, n in cats.most_common():
    print(f"  {cat:<35} {n}")

# Rename
shutil.copy(src, dest)
print(f"\nCopied to: {dest.name}")
print("(claude_classifications.json preserved for compatibility)")

# Show errors if file exists
import glob
err_files = list(OUTPUT_DIR.glob("batch_errors_msgbatch_0168*.json"))
if err_files:
    with open(err_files[0], encoding="utf-8") as f:
        errors = json.load(f)
    errs = errors if isinstance(errors, list) else errors.get("result", [])
    print(f"\nErrors ({len(errs)}):")
    for e in errs[:10]:
        print(f"  {e.get('qid','?')}: {e.get('error','?')}")
        print(f"    {e.get('raw','')[:120]}")
