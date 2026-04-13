"""
09_build_pearl_callouts.py
==========================
Injects 'Key Pearls' callout blocks into v5.docx study guide.
One green callout block per session that has a linked ingested JSON.
Uses unpack.py -> XML edit -> pack.py pipeline.

OUTPUT: ABFM_BoardPrep_ContentOutline_HY-Enriched-v5-pearls.docx
"""
import sys, json, os, re, zipfile, shutil, subprocess
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent
PROJECT_ROOT  = SCRIPT_DIR.parent.parent
V5_PATH       = SCRIPT_DIR.parent / "source" / "00_EX_content_outline_w_q.docx"
LINKS_JSON    = PROJECT_ROOT / "key_data_files" / "linked_refs_full.json"        # TODO: not yet migrated
INSERTS_JSON  = PROJECT_ROOT / "key_data_files" / "session_hy_inserts_v7.json"
OUT_DIR       = SCRIPT_DIR.parent / "outputs"
OUT_DOCX      = OUT_DIR / "BoardPrep-ContentOutline_HY-Enriched-v5-pearls.docx"
CANON_OUT     = OUT_DIR / "BoardPrep-ContentOutline_HY-Enriched-v5-pearls-canon.docx"
SCRIPTS_DIR   = SCRIPT_DIR.parent                                                 # M2 root (was guideline_extractor_v2)
UNPACK_PY     = SCRIPT_DIR / "unpack.py"                                          # TODO: unpack.py not yet migrated
PACK_PY       = SCRIPT_DIR / "pack.py"                                            # TODO: pack.py not yet migrated
UNPACK_DIR    = str(OUT_DIR / "v5_pearls_unpack")

# ── Load data ──────────────────────────────────────────────────────────────
with open(LINKS_JSON, encoding="utf-8") as f:
    links = json.load(f)
with open(INSERTS_JSON, encoding="utf-8") as f:
    inserts = json.load(f)

ref_map = {r["source_id"]: r for r in links["refs"]}
session_to_refs = links["session_to_refs"]

# ── XML color palette ──────────────────────────────────────────────────────
GREEN_DARK  = "1A5C38"
GREEN_LITE  = "E8F5EE"
GREEN_MID   = "2D7A4F"
AMBER       = "7B3F00"
AMBER_LITE  = "FEF3E2"
BLUE        = "2E75B6"
NAVY        = "1F3864"
WHITE       = "FFFFFF"
DARK        = "1A1A1A"
MID_GRAY    = "555555"

# ── XML builders ──────────────────────────────────────────────────────────
NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def shading_xml(fill):
    return f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'

def run_xml(text, bold=False, color=DARK, size=18, italic=False):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    b   = "<w:b/><w:bCs/>" if bold else ""
    it  = "<w:i/><w:iCs/>" if italic else ""
    preserve = ' xml:space="preserve"' if (text.startswith(' ') or text.endswith(' ')) else ''
    return f"""<w:r>
      <w:rPr>
        {b}{it}
        <w:color w:val="{color}"/>
        <w:sz w:val="{size}"/><w:szCs w:val="{size}"/>
        <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
      </w:rPr>
      <w:t{preserve}>{text}</w:t>
    </w:r>"""

def para_xml(inner_runs, fill=None, spB=60, spA=60, indent=0):
    shd   = f"<w:shd w:val='clear' w:color='auto' w:fill='{fill}'/>" if fill else ""
    ind   = f"<w:ind w:left='{indent}'/>" if indent else ""
    keep  = "<w:keepLines/><w:keepNext/>"
    return f"""<w:p>
    <w:pPr>
      {keep}
      <w:spacing w:before="{spB}" w:after="{spA}"/>
      {ind}
      <w:rPr>{shd}</w:rPr>
    </w:pPr>
    {inner_runs}
  </w:p>"""

def section_header_xml(label, fill, textColor=WHITE, spB=80, spA=0):
    return f"""<w:p>
    <w:pPr>
      <w:keepLines/><w:keepNext/>
      <w:spacing w:before="{spB}" w:after="{spA}"/>
      <w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>
    </w:pPr>
    {run_xml(label, bold=True, color=textColor, size=18)}
  </w:p>"""

def bullet_para_xml(text, indent=480):
    text_safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    preserve = ' xml:space="preserve"' if (text_safe.startswith(' ') or text_safe.endswith(' ')) else ''
    return f"""<w:p>
    <w:pPr>
      <w:keepLines/>
      <w:spacing w:before="30" w:after="30"/>
      <w:ind w:left="{indent}" w:hanging="240"/>
      <w:shd w:val="clear" w:color="auto" w:fill="{GREEN_LITE}"/>
    </w:pPr>
    <w:r><w:rPr>
      <w:color w:val="{DARK}"/>
      <w:sz w:val="18"/><w:szCs w:val="18"/>
      <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
    </w:rPr><w:t>\u2022</w:t></w:r>
    <w:r><w:rPr>
      <w:color w:val="{DARK}"/>
      <w:sz w:val="18"/><w:szCs w:val="18"/>
      <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
    </w:rPr><w:t{preserve}>{text_safe}</w:t></w:r>
  </w:p>"""

def build_pearl_block(session_id, session_title, refs_for_session):
    """Build the full XML block for one session's pearl callout."""
    parts = []

    # Top spacer
    parts.append(f"""<w:p><w:pPr><w:spacing w:before="80" w:after="0"/>
      <w:shd w:val="clear" w:color="auto" w:fill="{GREEN_DARK}"/>
    </w:pPr></w:p>""")

    # Banner header
    parts.append(section_header_xml(
        f"\U0001F4D6  KEY PEARLS \u2014 SESSION {session_id}  |  {session_title.upper()[:55]}",
        GREEN_DARK, WHITE, spB=60, spA=0
    ))

    for ref in refs_for_session:
        # Article sub-header
        parts.append(f"""<w:p>
          <w:pPr>
            <w:keepLines/><w:keepNext/>
            <w:spacing w:before="60" w:after="0"/>
            <w:shd w:val="clear" w:color="auto" w:fill="{GREEN_MID}"/>
          </w:pPr>
          {run_xml(ref['title'][:85], bold=True, color=WHITE, size=17)}
          {run_xml(f"  [{ref['tier']}]", bold=False, color=WHITE, size=16)}
        </w:p>""")

        # Summary (1 sentence)
        summary = ref.get("summary", "")
        if summary:
            first_sent = summary.split(".")[0] + "." if "." in summary else summary[:180]
            parts.append(para_xml(
                run_xml(first_sent[:220], color=DARK, size=18),
                fill=GREEN_LITE, spB=40, spA=20, indent=0
            ))

        # Top 4 recommendations
        recs = ref.get("recommendations", [])
        if recs:
            parts.append(section_header_xml("  Recommendations", GREEN_LITE, GREEN_DARK, spB=30, spA=0))
            for r in recs[:4]:
                text = r if isinstance(r, str) else r.get("recommendation", str(r))
                strength = "" if isinstance(r, str) else r.get("strength", "")
                suffix = f"  [{strength}]" if strength else ""
                parts.append(bullet_para_xml(text[:180] + suffix))

        # Top thresholds (inline compact)
        thresholds = ref.get("key_thresholds", [])
        if thresholds:
            thresh_texts = []
            for t in thresholds[:5]:
                if isinstance(t, dict):
                    thresh_texts.append(f"{t.get('parameter','?')}: {t.get('value','')}{t.get('unit','')}  ({t.get('context','')})")
                else:
                    thresh_texts.append(str(t))
            thresh_str = "   |   ".join(thresh_texts[:3])
            parts.append(f"""<w:p>
              <w:pPr>
                <w:keepLines/>
                <w:spacing w:before="40" w:after="20"/>
                <w:shd w:val="clear" w:color="auto" w:fill="{GREEN_LITE}"/>
              </w:pPr>
              {run_xml("Thresholds: ", bold=True, color=GREEN_DARK, size=17)}
              {run_xml(thresh_str[:250], color=DARK, size=17)}
            </w:p>""")

        # Red flags (if any)
        red_flags = ref.get("red_flags", [])
        if red_flags:
            rf_text = "   ·   ".join([str(r)[:60] for r in red_flags[:4]])
            _warning_xml = run_xml("⚠  Red Flags: ", bold=True, color=AMBER, size=17)
            parts.append(f"""<w:p>
              <w:pPr>
                <w:keepLines/>
                <w:spacing w:before="30" w:after="20"/>
                <w:shd w:val="clear" w:color="auto" w:fill="{AMBER_LITE}"/>
              </w:pPr>
              {_warning_xml}
              {run_xml(rf_text[:240], color=DARK, size=17)}
            </w:p>""")

    # Citation footer
    parts.append(f"""<w:p>
      <w:pPr>
        <w:keepLines/>
        <w:spacing w:before="30" w:after="60"/>
        <w:shd w:val="clear" w:color="auto" w:fill="{GREEN_DARK}"/>
      </w:pPr>
      {run_xml("Source: " + refs_for_session[0].get("citation","")[:120], italic=True, color=WHITE, size=16)}
    </w:p>""")

    return "\n".join(parts)

# ── Step 1: Unpack v5 ──────────────────────────────────────────────────────
print("Unpacking v5...")
if os.path.exists(UNPACK_DIR):
    # shutil.rmtree banned (NTFS); use PowerShell Remove-Item
    subprocess.run(
        ["powershell", "-Command",
         f"Remove-Item -Recurse -Force '{UNPACK_DIR}' -ErrorAction SilentlyContinue"],
        capture_output=True
    )
result = subprocess.run(
    ["python", UNPACK_PY, V5_PATH, UNPACK_DIR],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("UNPACK ERROR:", result.stderr)
    sys.exit(1)
print("  Unpacked OK")

# ── Step 2: Read XML ────────────────────────────────────────────────────────
xml_path = os.path.join(UNPACK_DIR, "word", "document.xml")
with open(xml_path, encoding="utf-8") as f:
    xml = f.read()
print(f"  XML loaded: {len(xml):,} chars")

# ── Step 3: Inject pearl blocks ─────────────────────────────────────────────
# Strategy: find each session's Heading1 paragraph (session title), then
# find the LAST callout block after it (blue ITE block), inject pearl block after.
# Session headings in v5 are: exact session title as Heading1

injected = 0
session_order = sorted(session_to_refs.keys(), key=lambda x: int(x))

for sess_id in session_order:
    sess_data  = inserts.get(sess_id, {})
    sess_title = sess_data.get("session_title", "")
    if not sess_title:
        continue
    ref_sids  = session_to_refs[sess_id]
    refs_data = [ref_map[s] for s in ref_sids if s in ref_map]
    if not refs_data:
        continue

    # Find session heading: <w:t>SESSION TITLE</w:t> within a Heading1 style para
    # Use the session title text to locate the right paragraph
    title_escaped = sess_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Pattern: find para with Heading1 style containing this title text
    pattern = re.compile(
        r'(<w:p\b[^>]*>(?:(?!<w:p\b).)*?<w:pStyle w:val="Heading1"/>(?:(?!<w:p\b).)*?' +
        re.escape(title_escaped) +
        r'(?:(?!</w:p>).)*?</w:p>)',
        re.DOTALL
    )
    m = pattern.search(xml)
    if not m:
        print(f"  [SKIP] Session {sess_id} — heading not found: {sess_title[:40]}")
        continue

    # Now find the end of the last colored paragraph block after this heading
    # (the ITE question callout). We look for the last paragraph with fill=1F3864 or 2E75B6
    # within the next 30,000 chars after the heading match
    heading_end = m.end()
    search_window = xml[heading_end:heading_end + 35000]

    # Find all positions of closing ITE callout blocks (the navy banner last para)
    # Look for the last occurrence of the navy shading in this window
    last_blue_end = -1
    for fm in re.finditer(r'<w:shd w:val="clear" w:color="auto" w:fill="1F3864"/>', search_window):
        # Walk forward to find the closing </w:p>
        para_close = search_window.find("</w:p>", fm.end())
        if para_close > 0:
            last_blue_end = heading_end + para_close + 6  # +6 for </w:p>

    if last_blue_end < 0:
        print(f"  [SKIP] Session {sess_id} — no blue callout block found after heading")
        continue

    # Build the pearl XML block
    pearl_xml = build_pearl_block(sess_id, sess_title, refs_data)

    # Inject after the last blue callout block
    xml = xml[:last_blue_end] + "\n" + pearl_xml + "\n" + xml[last_blue_end:]
    print(f"  [OK] Session {sess_id} — {sess_title[:40]} ({len(refs_data)} ref(s))")
    injected += 1

print(f"\nInjected: {injected} pearl blocks")

# ── Step 4: Write modified XML ──────────────────────────────────────────────
with open(xml_path, "w", encoding="utf-8") as f:
    f.write(xml)

# ── Step 5: Pack ────────────────────────────────────────────────────────────
print("\nPacking...")
result = subprocess.run(
    ["python", PACK_PY, UNPACK_DIR, OUT_DOCX, "--original", V5_PATH],
    capture_output=True, text=True, cwd=SCRIPTS_DIR
)
print(result.stdout)
if result.returncode != 0:
    print("PACK ERROR:", result.stderr)
    sys.exit(1)

# Copy to canonical
shutil.copy2(OUT_DOCX, CANON_OUT)
print(f"Output: {OUT_DOCX}")
print(f"Canonical: {CANON_OUT}")
print("\nDone.")
