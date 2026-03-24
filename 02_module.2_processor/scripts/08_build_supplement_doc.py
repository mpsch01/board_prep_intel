"""
08_build_supplement_doc.py

Creates a standalone ITE Supplement Question document.
Colors matched to the HY-Enriched outline (navy/blue palette).

Structure:
  - Title page header
  - Per session: banner -> 5 questions (header, stem, choices, answer)
  - End-of-document: Answer Key & Explanations glossary

Output: ABFM_BoardPrep_Supplement_ITE-Questions_v1.docx
"""
import sys, re, json, zipfile, shutil, os
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

BASE       = r"C:\Users\mpsch\Desktop\claude_knowledge"
SUPP_XLSX  = os.path.join(BASE, "board_prep", "aafp_integration", "02_working", "supplement_questions.xlsx")
Q_JSON     = os.path.join(BASE, "board_prep", "ite_exam", "03_database", "ite_questions_clean.json")
SRC_DOCX   = os.path.join(BASE, "00_canonical", "01_curriculum", "ABFM_BoardPrep_ContentOutline_HY-Enriched_v5.docx")
OUT_DOCX   = os.path.join(BASE, "00_canonical", "01_curriculum", "ABFM_BoardPrep_Supplement_ITE-Questions_v1.docx")
SUBSTITUTE = {"Q2020-036": "Q2025-033"}

# ── Palette (matched to outline) ──────────────────────────────────────────────
BANNER_FILL  = "1F3864"   # dark navy  — matches outline session banner
HEADER_FILL  = "2E75B6"   # blue       — matches outline sub-header
BODY_FILL    = "D6E4F7"   # light blue — matches outline question rows
ALT_FILL     = "EBF3FB"   # lighter    — alternating rows
ANSWER_FILL  = "2E75B6"   # blue       — answer row same as sub-header
BANNER_TXT   = "FFFFFF"
HEADER_TXT   = "FFFFFF"
BODY_TXT     = "1F3864"   # navy text on light blue
ANSWER_TXT   = "FFFFFF"
CORRECT_TXT  = "FFFFFF"

# Glossary palette — slightly darker variants to distinguish
GLOSS_BANNER = "1A2F50"
GLOSS_SESS   = "2C5F8A"
GLOSS_BODY   = "D6E4F7"
GLOSS_ALT    = "EBF3FB"

# ── Para ID counter ───────────────────────────────────────────────────────────
_pid = [0xD000]
def new_pid():
    _pid[0] += 1
    return f"{_pid[0]:08X}"

# ── XML helpers ───────────────────────────────────────────────────────────────
def esc(t):
    return (str(t).replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
                  .replace('"', "&quot;"))

def run(text, color, sz=18, bold=False, italic=False):
    b = "<w:b/><w:bCs/>" if bold else ""
    i = "<w:i/><w:iCs/>" if italic else ""
    sp = ' xml:space="preserve"' if text != text.strip() or "  " in text else ""
    return (f'<w:r><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/>'
            f'{b}{i}<w:color w:val="{color}"/>'
            f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>'
            f'<w:t{sp}>{esc(text)}</w:t></w:r>')

def make_para(fill, runs_xml, indent=False, sp_before=80, sp_after=40,
              border_top=None, keep_next=False):
    pid  = new_pid()
    bdr  = (f'<w:pBdr><w:top w:val="single" w:sz="8" w:space="1" '
            f'w:color="{border_top}"/></w:pBdr>') if border_top else ""
    shd  = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
    sp   = f'<w:spacing w:before="{sp_before}" w:after="{sp_after}"/>'
    ind  = '<w:ind w:left="200"/>' if indent else ""
    kn   = "<w:keepNext/>" if keep_next else ""
    return (f'<w:p w14:paraId="{pid}" w14:textId="77777777" '
            f'w:rsidR="00DD0001" w:rsidRDefault="00000000">'
            f'<w:pPr>{kn}{bdr}{shd}{sp}{ind}</w:pPr>'
            f'{runs_xml}</w:p>')

# ── Block builders ────────────────────────────────────────────────────────────

def build_doc_title():
    """Opening title block for the supplement document."""
    paras = []
    paras.append(make_para("1F3864",
        run("  ABFM BOARD PREP — ITE SUPPLEMENT QUESTIONS", "FFFFFF", sz=24, bold=True),
        sp_before=200, sp_after=60))
    paras.append(make_para("2E75B6",
        run("  In-Training Examination Questions  •  2020–2025  •  240 Questions  •  48 Sessions",
            "FFFFFF", sz=17, italic=True),
        sp_before=40, sp_after=120))
    return "\n".join(paras)

def build_session_banner(sess_id, sess_title, n_q):
    txt = f"  \u25a0  Session {sess_id:02d}  \u2014  {sess_title}   \u2022   {n_q} questions"
    return make_para(BANNER_FILL,
                     run(txt, BANNER_TXT, sz=20, bold=True),
                     sp_before=200, sp_after=60,
                     border_top=BANNER_FILL, keep_next=True)

def build_q_header(rank, qid, year, body_sys, subcat, fill):
    txt = (f"  Q{rank}   \u2022   {qid}   \u2022   {year}"
           f"   \u2022   {body_sys}   \u2022   {subcat}")
    return make_para(HEADER_FILL,
                     run(txt, HEADER_TXT, sz=17, bold=True),
                     sp_before=80, sp_after=30, keep_next=True)

def build_stem(text, fill):
    return make_para(fill,
                     run("  " + text, BODY_TXT, sz=18),
                     indent=False, sp_before=60, sp_after=20, keep_next=True)

def build_choice(letter, text, fill):
    label = run(f"  {letter})  ", BODY_TXT, sz=18, bold=True)
    body  = run(text, BODY_TXT, sz=18)
    return make_para(fill, label + body, indent=True, sp_before=20, sp_after=20)

def build_answer(correct_letter, correct_text):
    label  = run("  Answer:  ", ANSWER_TXT, sz=18, bold=True)
    answer = run(f"{correct_letter})  {correct_text}", ANSWER_TXT, sz=18, bold=True)
    return make_para(ANSWER_FILL, label + answer,
                     indent=True, sp_before=60, sp_after=80)

def build_session_block(sess_id, sess_title, questions):
    paras = [build_session_banner(sess_id, sess_title, len(questions))]
    for rank, q in enumerate(questions, 1):
        fill = BODY_FILL if rank % 2 == 1 else ALT_FILL
        paras.append(build_q_header(rank, q["question_id"], q["exam_year"],
                                    q["body_system"], q["subcategory"], fill))
        paras.append(build_stem(q["question_text"], fill))
        for c in q["choices"]:
            paras.append(build_choice(c["letter"], c["text"], fill))
        paras.append(build_answer(q["correct_letter"], q["correct_text"]))
    return "\n".join(paras)

# ── Glossary ──────────────────────────────────────────────────────────────────

def build_glossary(all_session_data):
    paras = []
    paras.append(make_para(GLOSS_BANNER,
        run("  \u25a0  ANSWER KEY & EXPLANATIONS", "FFFFFF", sz=22, bold=True),
        sp_before=300, sp_after=60, border_top=GLOSS_BANNER))
    paras.append(make_para(GLOSS_SESS,
        run("  All explanations sourced from ABFM ITE question bank (2020\u20132025). "
            "Organized by session.", "FFFFFF", sz=15, italic=True),
        sp_before=40, sp_after=100))

    for sess_id, sess_title, questions in all_session_data:
        paras.append(make_para(GLOSS_SESS,
            run(f"  Session {sess_id:02d} \u2014 {sess_title}", "FFFFFF", sz=18, bold=True),
            sp_before=120, sp_after=40))

        for rank, q in enumerate(questions, 1):
            fill = GLOSS_BODY if rank % 2 == 1 else GLOSS_ALT
            # Header
            hdr = (f"  Q{rank}  |  {q['question_id']}  |  {q['exam_year']}"
                   f"  |  {q['body_system']}  |  {q['subcategory']}")
            paras.append(make_para(fill,
                run(hdr, "1F3864", sz=16, bold=True),
                indent=True, sp_before=60, sp_after=20))
            # Answer
            paras.append(make_para(fill,
                run(f"  Answer: {q['correct_letter']})  {q['correct_text']}",
                    "1F3864", sz=17, bold=True),
                indent=True, sp_before=20, sp_after=20))
            # Explanation
            expl_l = run("  EXPLANATION  ", "333333", sz=15, bold=True)
            expl_b = run(q["explanation"], "444444", sz=15)
            paras.append(make_para(fill, expl_l + expl_b,
                indent=True, sp_before=20, sp_after=20))
            # Reference
            if q.get("reference"):
                ref_l = run("  REFERENCE  ", "333333", sz=14, bold=True)
                ref_b = run(q["reference"], "555555", sz=14, italic=True)
                paras.append(make_para(fill, ref_l + ref_b,
                    indent=True, sp_before=10, sp_after=50))
    return "\n".join(paras)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Load data
    with open(Q_JSON, encoding="utf-8") as f:
        qs = {q["question_id"]: q for q in json.load(f)}
    print(f"Loaded {len(qs)} questions")

    df_summary = pd.read_excel(SUPP_XLSX, sheet_name="Summary")
    sessions_sorted = []
    session_titles  = {}
    session_qs      = {}

    for _, row in df_summary.iterrows():
        label    = str(row["Session"])
        parts    = label.split("\u2014", 1)
        sess_id  = int(parts[0].strip())
        title    = parts[1].strip() if len(parts) > 1 else label
        session_titles[sess_id] = title

        sheet    = f"S{sess_id:02d}"
        df_sess  = pd.read_excel(SUPP_XLSX, sheet_name=sheet)
        df_supp  = df_sess[df_sess["Set"] == "SUPPLEMENT"]
        q_list   = []
        for _, qrow in df_supp.iterrows():
            qid = SUBSTITUTE.get(str(qrow["QID"]), str(qrow["QID"]))
            if qid in qs and not qs[qid]["needs_review"]:
                q_list.append(qs[qid])
            else:
                print(f"  WARNING: {qid} skipped (session {sess_id})")
        session_qs[sess_id] = q_list
        sessions_sorted.append(sess_id)

    sessions_sorted.sort()
    total_q = sum(len(v) for v in session_qs.values())
    print(f"Sessions: {len(sessions_sorted)}, Total questions: {total_q}")

    # Build all content XML paragraphs
    content_parts = [build_doc_title()]
    for sess_id in sessions_sorted:
        q_list = session_qs[sess_id]
        if not q_list:
            continue
        content_parts.append(build_session_block(sess_id, session_titles[sess_id], q_list))

    # Glossary
    all_sess_data = [(sid, session_titles[sid], session_qs[sid])
                     for sid in sessions_sorted if session_qs[sid]]
    content_parts.append(build_glossary(all_sess_data))
    print(f"Glossary: {sum(len(x[2]) for x in all_sess_data)} entries")

    all_content_xml = "\n".join(content_parts)

    # Extract namespace declarations + sectPr from v5 source
    shutil.copy2(SRC_DOCX, OUT_DOCX)
    with zipfile.ZipFile(OUT_DOCX, "r") as z:
        src_xml = z.read("word/document.xml").decode("utf-8")

    # Extract the root <w:document> opening tag with all namespaces
    root_open = re.search(r"(<w:document\b[^>]*>)", src_xml, re.DOTALL).group(1)
    # Extract sectPr (page layout) from source
    sect_pr   = re.search(r"(<w:sectPr\b.*?</w:sectPr>)", src_xml, re.DOTALL)
    sect_xml  = sect_pr.group(1) if sect_pr else ""

    new_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        + root_open + "\n"
        + "<w:body>\n"
        + all_content_xml + "\n"
        + sect_xml + "\n"
        + "</w:body>\n"
        + "</w:document>"
    )

    tmp = OUT_DOCX + ".tmp"
    with zipfile.ZipFile(OUT_DOCX, "r") as zin:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, new_xml.encode("utf-8"))
                else:
                    zout.writestr(item, zin.read(item.filename))
    os.replace(tmp, OUT_DOCX)
    print(f"\nDone: {OUT_DOCX}")
    print(f"XML size: {len(new_xml):,} chars")


if __name__ == "__main__":
    main()
