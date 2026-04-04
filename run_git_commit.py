"""One-shot git helper — run via Desktop Commander, then delete."""
import subprocess, os, pathlib

REPO = pathlib.Path(r"C:\Users\mpsch\Desktop\claude_knowledge\00_#PROJECT_OVERHAUL")
LOG  = REPO / "git_commit_result.txt"

MSG = """feat: ITE PDF pipeline + AAFP QA deliverables + M1 warehouse restructure

- extract_ite_year.py: PDF-native ITE exam extractor (PDF -> DB, QID at INSERT)
- classify_ite_year.py: SBERT+XGBoost body system classifier (separated for load time)
- build_aafp_qa_deliverables.py: 13-file AAFP Q&A generator (DOCX + XLSX, ~100Q each)
- M1 restructure: practice_questions/ + ite_source/ data pools added
- repo_pre_severance.md: full 123-script inventory + Option B path analysis
- Sweep cleanup: archive_canonical -> _archive_, aafp_transcripts renamed, 11 script path fixes
- BATON 035 + 036 written; CLAUDE.md updated

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"""

results = []

def run(cmd):
    r = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, shell=True)
    out = (r.stdout + r.stderr).strip()
    results.append(f"$ {cmd}\n{out}\n")
    return r.returncode, out

# Remove stale lock if present
lock = REPO / ".git" / "index.lock"
if lock.exists():
    lock.unlink()
    results.append("Removed stale index.lock\n")

run("git add -A")
rc, out = run(f'git commit -m "{MSG}"')
run("git log --oneline -3")

LOG.write_text("\n".join(results), encoding="utf-8")
print(f"Done. rc={rc}. See git_commit_result.txt")
