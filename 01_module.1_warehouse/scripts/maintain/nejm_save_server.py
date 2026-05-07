"""Tiny CORS-enabled HTTP server for browser-side PDF uploads.

Listens on http://localhost:5454/. Accepts POST /save with form fields:
  file       - the PDF binary
  article_id, tier, author, year

Saves to the appropriate tier folder with codon filename.
Designed for browser-driven NEJM downloads where we can't pass the bytes
back through the Chrome MCP tool result.
"""

from __future__ import annotations

import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import cgi
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
TIER_ROOT = PROJECT_ROOT / "01_module.1_warehouse" / "citation_files" / "ITE"

VALID_TIERS = {"VC_pass", "VC_fail", "local_lite", "right_click"}


def normalize_author(author: str) -> str:
    a = re.split(r"[\s,]+", author.strip())[0]
    a = re.sub(r"[^A-Za-z\-']", "", a)
    if not a:
        return "Unknown"
    return a[0].upper() + a[1:]


def codon_filename(author: str, year: str, article_id: str) -> str:
    return f"{normalize_author(author)}_{year}#@#{article_id}@#@.pdf"


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/save":
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        ctype = self.headers.get("Content-Type", "")
        if not ctype.startswith("multipart/form-data"):
            self.send_response(400)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"need multipart/form-data"}')
            return
        try:
            fs = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype},
            )
            article_id = fs.getvalue("article_id", "")
            tier = fs.getvalue("tier", "")
            author = fs.getvalue("author", "")
            year = fs.getvalue("year", "")
            file_field = fs["file"] if "file" in fs else None
            if not (article_id and tier in VALID_TIERS and author and year and file_field is not None):
                self.send_response(400)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"missing/invalid fields"}')
                return
            data = file_field.file.read() if hasattr(file_field, "file") else file_field.value
            if not data or not data[:4].startswith(b"%PDF"):
                self.send_response(400)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"not a pdf"}')
                return
            fname = codon_filename(author, year, article_id)
            dest = TIER_ROOT / tier / fname
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            print(f"SAVED {article_id} -> {fname} ({len(data)} bytes)", flush=True)
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            import json
            self.wfile.write(json.dumps({"ok": True, "saved": str(dest), "size": len(data)}).encode())
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            self.send_response(500)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error":"{e}"}}'.encode())

    def log_message(self, format, *args):
        # Suppress default access logs to keep output clean
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5454
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"NEJM save server listening on http://127.0.0.1:{port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
