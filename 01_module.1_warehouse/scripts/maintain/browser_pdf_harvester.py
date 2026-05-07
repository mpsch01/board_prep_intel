"""
browser_pdf_harvester.py
========================
Downloads JAMA and NEJM PDFs by acting as a local HTTP server that the user's
already-authenticated browser fetches from.

HOW IT WORKS
────────────
1. Reads NEJM/JAMA articles from exa_pdf_queue.csv
2. Starts a local HTTP server at http://localhost:8765
3. Serves a self-contained HTML page that:
     - Fetches each PDF URL using the browser's real authenticated session
     - POSTs the raw bytes back to the local server
4. Python receives the bytes and saves each PDF to the correct tier folder

NO cookies to extract, NO Playwright, NO Cloudflare. The browser's existing
login session does the work.

USAGE
────────────
1. Run this script:
       python browser_pdf_harvester.py

2. Open http://localhost:8765 in your Chrome browser (already logged in to NEJM/JAMA).

3. Click "Start Downloads". Watch progress. When done, the page shows a summary.

OPTIONS
────────────
    python browser_pdf_harvester.py --journal nejm      # NEJM only
    python browser_pdf_harvester.py --journal jama      # JAMA only
    python browser_pdf_harvester.py --journal both      # both (default)
    python browser_pdf_harvester.py --port 8765         # change port
"""

import os, re, csv, json, base64, argparse, threading, time
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
PDF_ROOT     = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"
QUEUE_CSV    = SCRIPT_DIR / "exa_pdf_queue.csv"
PREV_RESULTS = SCRIPT_DIR / "exa_download_results.csv"
RESULTS_CSV  = SCRIPT_DIR / "browser_harvest_results.csv"
LOG_PATH     = SCRIPT_DIR / "browser_harvest.log"

CODON_RE = re.compile(r'#@#(ART-\d+)@#@')
MIN_PDF_BYTES = 1024
MAX_PDF_MB    = 50

# ── Globals (shared between server and main thread) ────────────────────────
_articles     = []     # list of article dicts with _url, _journal, etc.
_results      = {}     # article_id → status dict
_server       = None
_log_fh       = None


def log(msg):
    print(msg, flush=True)
    if _log_fh:
        _log_fh.write(msg + "\n")
        _log_fh.flush()


# ── Filename helpers ───────────────────────────────────────────────────────

def make_codon_filename(row):
    author      = (row.get("author1") or "Unknown").strip()
    author_1st  = re.split(r'[\s,;/]', author)[0]
    author_safe = re.sub(r'[^\w\-]', '', author_1st) or "Unknown"
    year        = str(row.get("year") or "0000").strip()
    art_id      = row.get("article_id", "ART-0000")
    return f"{author_safe}_{year}#@#{art_id}@#@.pdf"

def dest_folder(row):
    return PDF_ROOT / row.get("tier", "VC_fail")


# ── URL helpers ────────────────────────────────────────────────────────────

def nejm_to_pdf_url(url):
    if "/doi/pdf/" in url:
        return url.split("?")[0]
    for seg in ["/doi/full/", "/doi/abs/"]:
        if seg in url:
            return url.replace(seg, "/doi/pdf/").split("?")[0]
    m = re.search(r'(https?://(?:www\.)?nejm\.org)/doi/(10\.\d+/\S+)', url)
    if m:
        doi = m.group(2).split("?")[0].rstrip("/")
        return f"{m.group(1)}/doi/pdf/{doi}"
    return url

def jama_article_url(url):
    """Return the JAMA article page URL (not PDF — browser will find PDF link)."""
    return url


# ── Queue loader ───────────────────────────────────────────────────────────

def get_art_ids_on_disk():
    found = set()
    for f in PDF_ROOT.rglob("*.pdf"):
        m = CODON_RE.search(f.name)
        if m:
            found.add(m.group(1))
    return found

def load_prev_ok():
    done = set()
    if not PREV_RESULTS.exists():
        return done
    with open(PREV_RESULTS, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "ok":
                done.add(row.get("article_id", ""))
    # Also check browser_harvest_results
    if RESULTS_CSV.exists():
        with open(RESULTS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("status") == "ok":
                    done.add(row.get("article_id", ""))
    return done

def load_targets(journal_filter):
    if not QUEUE_CSV.exists():
        log(f"ERROR: {QUEUE_CSV} not found")
        return []
    on_disk   = get_art_ids_on_disk()
    prev_ok   = load_prev_ok()
    skip_ids  = on_disk | prev_ok

    rows = []
    with open(QUEUE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row.get("top_url", "")
            if not url:
                continue
            art_id = row.get("article_id", "")
            if art_id in skip_ids:
                continue
            is_nejm = "nejm.org" in url.lower()
            is_jama = "jamanetwork.com" in url.lower()
            if journal_filter == "nejm" and not is_nejm:
                continue
            if journal_filter == "jama" and not is_jama:
                continue
            if journal_filter == "both" and not (is_nejm or is_jama):
                continue
            if is_nejm:
                row["_url"]     = nejm_to_pdf_url(url)
                row["_journal"] = "nejm"
            else:
                row["_url"]     = jama_article_url(url)
                row["_journal"] = "jama"
            row["_fname"]   = make_codon_filename(row)
            row["_folder"]  = str(dest_folder(row))
            rows.append(row)
    return rows


# ── Results writer ─────────────────────────────────────────────────────────

def append_result(data):
    fields = ["article_id", "tier", "journal", "status", "bytes",
              "dest_filename", "url_used", "title", "author1", "year"]
    write_header = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerow(data)


# ── HTML page builder ──────────────────────────────────────────────────────

def build_html(articles, port):
    articles_json = json.dumps([
        {
            "article_id": a["article_id"],
            "url":        a["_url"],
            "journal":    a["_journal"],
            "fname":      a["_fname"],
            "title":      (a.get("title") or "")[:60],
        }
        for a in articles
    ], indent=2)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PDF Harvester — {len(articles)} articles</title>
<style>
  body {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }}
  h2   {{ color: #4fc3f7; }}
  #log {{ height: 400px; overflow-y: auto; background: #0d0d1a; padding: 10px;
          border: 1px solid #333; font-size: 12px; white-space: pre-wrap; }}
  .ok  {{ color: #81c784; }}
  .err {{ color: #e57373; }}
  .inf {{ color: #4fc3f7; }}
  button {{ background: #4fc3f7; color: #000; border: none; padding: 10px 24px;
             font-size: 14px; cursor: pointer; border-radius: 4px; margin: 8px 4px; }}
  button:disabled {{ background: #555; color: #888; cursor: default; }}
  #progress {{ margin: 10px 0; font-size: 13px; }}
</style>
</head>
<body>
<h2>🗂 PDF Harvester</h2>
<p id="status">Ready — {len(articles)} articles queued.</p>
<button id="btnStart" onclick="startDownloads()">▶ Start Downloads</button>
<button onclick="document.getElementById('log').innerHTML=''">Clear Log</button>
<div id="progress"></div>
<div id="log"></div>

<script>
const ARTICLES  = {articles_json};
const PORT      = {port};
const BATCH     = 3;   // concurrent fetches
let done = 0, ok = 0, failed = 0;

function logLine(cls, msg) {{
  const d = document.getElementById('log');
  d.innerHTML += '<span class="' + cls + '">' + msg + '\\n</span>';
  d.scrollTop = d.scrollHeight;
}}

function updateProgress() {{
  document.getElementById('progress').textContent =
    `[${{done}}/${{ARTICLES.length}}]  ✓ ${{ok}}  ✗ ${{failed}}`;
}}

async function fetchPdf(art) {{
  try {{
    const resp = await fetch(art.url, {{credentials: 'include'}});
    if (!resp.ok) {{
      logLine('err', `  ✗ ${{art.article_id}} HTTP ${{resp.status}} — ${{art.url}}`);
      return {{article_id: art.article_id, status: 'http_' + resp.status, bytes: 0}};
    }}
    const buf   = await resp.arrayBuffer();
    const bytes = new Uint8Array(buf);
    // Check PDF magic bytes
    if (bytes[0] !== 0x25 || bytes[1] !== 0x50 || bytes[2] !== 0x44 || bytes[3] !== 0x46) {{
      logLine('err', `  ✗ ${{art.article_id}} not a PDF (${{buf.byteLength}}B)`);
      return {{article_id: art.article_id, status: 'not_pdf', bytes: buf.byteLength}};
    }}
    // Convert to base64 in chunks to avoid stack overflow on large arrays
    let b64 = '';
    const chunkSize = 8192;
    for (let i = 0; i < bytes.length; i += chunkSize) {{
      b64 += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
    }}
    b64 = btoa(b64);
    // POST to local server
    const postResp = await fetch(`http://localhost:${{PORT}}/save`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        article_id: art.article_id,
        fname:      art.fname,
        journal:    art.journal,
        url:        art.url,
        b64:        b64,
      }})
    }});
    const result = await postResp.json();
    if (result.ok) {{
      logLine('ok', `  ✓ ${{art.article_id}} ${{art.fname}} (${{Math.round(buf.byteLength/1024)}}KB)`);
      return {{article_id: art.article_id, status: 'ok', bytes: buf.byteLength}};
    }} else {{
      logLine('err', `  ✗ ${{art.article_id}} save failed: ${{result.error}}`);
      return {{article_id: art.article_id, status: 'save_failed', bytes: buf.byteLength}};
    }}
  }} catch(e) {{
    logLine('err', `  ✗ ${{art.article_id}} ${{e.message}}`);
    return {{article_id: art.article_id, status: 'error', bytes: 0}};
  }}
}}

async function startDownloads() {{
  document.getElementById('btnStart').disabled = true;
  document.getElementById('status').textContent = 'Downloading...';
  logLine('inf', `Starting ${{ARTICLES.length}} articles (batch size ${{BATCH}})...\\n`);

  for (let i = 0; i < ARTICLES.length; i += BATCH) {{
    const batch  = ARTICLES.slice(i, i + BATCH);
    const results = await Promise.all(batch.map(fetchPdf));
    for (const r of results) {{
      done++;
      if (r.status === 'ok') ok++; else failed++;
    }}
    updateProgress();
    // Small pause between batches to avoid hammering the server
    await new Promise(res => setTimeout(res, 500));
  }}

  document.getElementById('status').textContent =
    `Done — ${{ok}} downloaded, ${{failed}} failed`;
  logLine('inf', `\\n=== COMPLETE: ${{ok}} ok / ${{failed}} failed ===`);
  logLine('inf', `You can now press Ctrl+C in the terminal to stop the server.`);
}}
</script>
</body>
</html>"""


# ── HTTP request handler ───────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass   # suppress default access log

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html = build_html(_articles, _server.server_address[1]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self._cors()
            self.end_headers()
            self.wfile.write(html)

        elif self.path == "/done":
            # Browser signals completion — just acknowledge, don't shut down.
            # Press Ctrl+C in the terminal when finished.
            self.send_response(200)
            self._cors()
            self.end_headers()
            self.wfile.write(b"done")

        elif self.path == "/status":
            payload = json.dumps({
                "total":  len(_articles),
                "done":   len(_results),
                "ok":     sum(1 for r in _results.values() if r["status"] == "ok"),
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(payload)

        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data       = json.loads(body)
            art_id     = data["article_id"]
            fname      = data["fname"]
            journal    = data["journal"]
            url_used   = data["url"]
            pdf_bytes  = base64.b64decode(data["b64"])

            # Find the matching article for metadata
            art = next((a for a in _articles if a["article_id"] == art_id), {})
            folder = Path(art.get("_folder", str(PDF_ROOT / "VC_fail")))

            if len(pdf_bytes) < MIN_PDF_BYTES:
                raise ValueError(f"Too small: {len(pdf_bytes)} bytes")
            if len(pdf_bytes) > MAX_PDF_MB * 1024 * 1024:
                raise ValueError(f"Too large: {len(pdf_bytes)//1024//1024}MB")
            if pdf_bytes[:4] != b"%PDF":
                raise ValueError(f"Not a PDF (magic: {pdf_bytes[:4]})")

            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / fname
            dest.write_bytes(pdf_bytes)

            kb = len(pdf_bytes) // 1024
            log(f"  ✓ {art_id} [{journal}] {fname} ({kb}KB)")
            _results[art_id] = {"status": "ok", "bytes": len(pdf_bytes)}
            append_result({
                "article_id":  art_id,
                "tier":        art.get("tier", ""),
                "journal":     journal,
                "status":      "ok",
                "bytes":       len(pdf_bytes),
                "dest_filename": fname,
                "url_used":    url_used,
                "title":       art.get("title", ""),
                "author1":     art.get("author1", ""),
                "year":        art.get("year", ""),
            })

            resp = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(resp)

        except Exception as e:
            log(f"  ✗ Save error for {data.get('article_id','?')}: {e}")
            _results[data.get("article_id", "?")] = {"status": "error", "bytes": 0}
            append_result({
                "article_id":  data.get("article_id", "?"),
                "tier":        "",
                "journal":     data.get("journal", ""),
                "status":      "error",
                "bytes":       0,
                "dest_filename": data.get("fname", ""),
                "url_used":    data.get("url", ""),
                "title": "", "author1": "", "year": "",
            })
            resp = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(resp)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    global _articles, _server, _log_fh

    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", default="both",
                        choices=["nejm", "jama", "both"])
    parser.add_argument("--port",    type=int, default=8765)
    args = parser.parse_args()

    _log_fh = open(LOG_PATH, "w", encoding="utf-8")
    log(f"=== browser_pdf_harvester.py — {datetime.now().isoformat()} ===")
    log(f"journal={args.journal}  port={args.port}\n")

    _articles = load_targets(args.journal)
    if not _articles:
        log("No targets found (all already on disk or no matching queue entries).")
        _log_fh.close()
        return

    by_j = {}
    for a in _articles:
        by_j[a["_journal"]] = by_j.get(a["_journal"], 0) + 1
    for j, n in by_j.items():
        log(f"  {j}: {n} articles")
    log(f"  Total: {len(_articles)}\n")

    _server = HTTPServer(("localhost", args.port), Handler)
    log(f"Server started at http://localhost:{args.port}")
    log(f"\n{'='*55}")
    log(f"  Open this URL in Chrome (already logged in to NEJM/JAMA):")
    log(f"  http://localhost:{args.port}")
    log(f"  Then click 'Start Downloads'.")
    log(f"{'='*55}\n")

    try:
        _server.serve_forever()
    except KeyboardInterrupt:
        pass

    ok     = sum(1 for r in _results.values() if r["status"] == "ok")
    failed = sum(1 for r in _results.values() if r["status"] != "ok")
    log(f"\n{'═'*50}")
    log(f"📦 Harvest Complete")
    log(f"{'═'*50}")
    log(f"  ✓ downloaded: {ok}")
    log(f"  ✗ failed:     {failed}")
    log(f"  Results: {RESULTS_CSV}")
    _log_fh.close()


if __name__ == "__main__":
    main()
