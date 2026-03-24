"""
strip_inline_refs.py
====================
Removes the inline "Ref: ..." lines embedded inside explanation paragraphs
in ABFM_ITE_QuestionBank_2020-2025.docx.

These are duplicates of the standalone italic REFERENCE paragraph below each question.
Keeps: the standalone REFERENCE paragraph (italic, labeled)
Removes: the "Ref: ..." text run(s) at the end of the explanation paragraph

Pattern to remove: paragraphs (or line-break runs) containing text starting with "Ref: "
that appear inside the explanation paragraph body (NOT in the standalone REFERENCE para).

Strategy:
  - The explanation paragraph contains <w:t> elements with "Ref: " text
  - These are preceded by <w:br/> line breaks within the same <w:p>
  - Remove the <w:r> elements containing "Ref: " text AND the preceding <w:r><w:br/>
    that introduces that line, up to the end of that paragraph

  - The standalone REFERENCE paragraph is identified by having a bold "REFERENCE" label run
    followed by an italic run — leave this untouched.
"""
import zipfile, re, sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')

SRC  = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\02_question_bank\ABFM_ITE_QuestionBank_2020-2025.docx'
DST  = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\02_question_bank\ABFM_ITE_QuestionBank_2020-2025.docx'
BACK = r'C:\Users\mpsch\Desktop\claude_knowledge\00_canonical\02_question_bank\previous_versions\ABFM_ITE_QuestionBank_2020-2025_pre-dedup.docx'

os.makedirs(os.path.dirname(BACK), exist_ok=True)
shutil.copy2(SRC, BACK)
print(f'Backup saved: {BACK}')

with zipfile.ZipFile(SRC, 'r') as z:
    files = {n: z.read(n) for n in z.namelist()}

xml = files['word/document.xml'].decode('utf-8')
original_len = len(xml)

# ── Strategy ──────────────────────────────────────────────────────────────────
# Inside explanation paragraphs, the Ref line looks like:
#
#   <w:r>
#     <w:br/>
#     <w:t>Ref: Smith DK...</w:t>
#   </w:r>
#   <w:r>                          ← sometimes ref wraps to next run
#     <w:br/>
#     <w:t>2020;101(6):341-349.</w:t>
#   </w:r>
#
# The ref text begins with "Ref: " and may continue across 1-2 more <w:r> runs
# (wrapped lines). We need to remove the <w:r><w:br/><w:t>Ref:... through
# the end of the paragraph's Ref runs.
#
# Approach: regex on the raw XML to strip <w:r> blocks that contain "Ref: "
# and subsequent continuation runs (those that follow the Ref: run and are
# plain text runs with no rPr styling — i.e., continuation of the citation).
#
# The standalone REFERENCE paragraph has its own <w:p> with a bold "REFERENCE"
# label — it does NOT contain "Ref: " text so it will not be touched.

# Pattern: a <w:r> containing a <w:br/> followed by <w:t> starting with "Ref: "
# plus any immediately following <w:r> blocks that are continuation lines
# (have <w:br/> and no <w:b/> or <w:i/> in rPr — plain continuation runs)

# Step 1: remove the primary Ref: run (with preceding line-break)
ref_run_pat = re.compile(
    r'<w:r>\s*<w:br/>\s*<w:t[^>]*>Ref:.*?</w:t>\s*</w:r>',
    re.DOTALL)

# Step 2: remove continuation runs that follow — they look like:
# <w:r>\n  <w:br/>\n  <w:t>2020;101(6):341-349.</w:t>\n</w:r>
# These are tricky because they could also be legitimate text.
# Better approach: remove from the first "Ref: " run to the end of that paragraph's
# Ref lines by capturing the Ref: run + ALL subsequent runs until the </w:p>

# More precise: find the <w:r> containing Ref: and remove it plus any runs
# that come after it within the same paragraph (they are always the last content
# before </w:p> since ABFM puts the Ref at the very end of the explanation para)

# Strategy: within each paragraph, if it contains "Ref: ", remove everything
# from the first <w:r> that contains "Ref: " to the end of the paragraph's
# content (before </w:p>), then close the paragraph normally.

# This is safest done paragraph by paragraph.

def strip_ref_from_para(para_xml):
    """Remove Ref: run and all subsequent runs from an explanation paragraph."""
    # Find position of first run containing "Ref: "
    ref_idx = para_xml.find('>Ref: ')
    if ref_idx == -1:
        ref_idx = para_xml.find('>Ref:</w:t>')  # edge case
    if ref_idx == -1:
        return para_xml, False

    # Walk back to find the start of the <w:r> containing this Ref text
    run_start = para_xml.rfind('<w:r>', 0, ref_idx)
    if run_start == -1:
        return para_xml, False

    # Everything from run_start to </w:p> should be removed (Ref + continuations)
    # Find the closing </w:p>
    close_p = para_xml.rfind('</w:p>')
    if close_p == -1:
        return para_xml, False

    stripped = para_xml[:run_start] + para_xml[close_p:]
    return stripped, True

# Split XML into paragraphs, process each
# We'll work on paragraph-level chunks
para_pat = re.compile(r'(<w:p\b[^>]*>.*?</w:p>)', re.DOTALL)

removed_count = 0
def process_para(m):
    global removed_count
    para = m.group(1)
    # Only touch explanation paragraphs (contain "Ref: " but NOT "REFERENCE" label)
    if 'Ref: ' not in para:
        return para
    if '>REFERENCE<' in para or '>REFERENCE ' in para:
        return para   # standalone REFERENCE label para — leave alone
    new_para, changed = strip_ref_from_para(para)
    if changed:
        removed_count += 1
    return new_para

new_xml = para_pat.sub(process_para, xml)
new_len = len(new_xml)

print(f'Ref: lines removed from explanation paragraphs: {removed_count}')
print(f'XML size: {original_len:,} -> {new_len:,} chars  (reduced by {original_len-new_len:,})')

files['word/document.xml'] = new_xml.encode('utf-8')

# Write to temp first, then replace
tmp = SRC + '.tmp'
with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name, data in files.items():
        zout.writestr(name, data)

os.replace(tmp, DST)
before_mb = os.path.getsize(BACK) / 1024/1024
after_mb  = os.path.getsize(DST)  / 1024/1024
print(f'File size: {before_mb:.2f} MB -> {after_mb:.2f} MB')
print('Done.')
