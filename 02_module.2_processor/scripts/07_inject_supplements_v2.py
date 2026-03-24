"""
07_inject_supplements_v2.py

Injects ITE supplement question blocks into HY-Enriched v5 docx.
One block per session (5 questions), inserted after last content paragraph
before the next session heading.

Also appends end-of-document Answer Key & Explanations glossary.

Callout format per question:
  [banner row]  ■ ITE SUPPLEMENT  •  Session XX  •  5 questions
  [q header]    Q1 | QID | Year | Body System | Subcategory
  [stem rows]   question text (wrapped)
  [choice rows] A) ...  B) ...  C) ...
  [answer row]  Answer: X) correct text (bolded)

End-of-document glossary (organized by session):
  Session 02 — Q1 (QID): explanation | Ref: reference

Inputs:
  supplement_questions.xlsx  (session -> QID assignments)
  ite_questions_clean.json   (parsed question bank)
  v5.docx                    (clean base document)

Output:
  ABFM_BoardPrep_ContentOutline_HY-Enriched_v7.docx
"""
import sys, re, json, zipfile, shutil, os
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = r"C:\Users\mpsch\Desktop\claude_knowledge"
SUPP_XLSX = os.path.join(BASE, "board_prep", "aafp_integration", "02_working", "supplement_questions.xlsx")
Q_JSON    = os.path.join(BASE, "board_prep", "ite_exam", "03_database", "ite_questions_clean.json")
SRC_DOCX  = os.path.join(BASE, "00_canonical", "01_curriculum", "ABFM_BoardPrep_ContentOutline_HY-Enriched_v5.docx")
OUT_DOCX  = os.path.join(BASE, "00_canonical", "01_curriculum", "ABFM_BoardPrep_ContentOutline_HY-Enriched_v7.docx")
SUBSTITUTE = {"Q2020-036": "Q2025-033"}

# ── Colors ────────────────────────────────────────────────────────────────────
BANNER_FILL = "1B5E6E"
HEADER_FILL = "2E9E7E"
BODY_FILL   = "D4EDE7"
ANSWER_FILL = "A8D8CE"


# ── Para ID counter ───────────────────────────────────────────────────────────
_pid = [0xC000]
def new_pid():
    _pid[0] += 1
    return f"{_pid[0]:08X}"

# ── XML helpers ───────────────────────────────────────────────────────────────
def esc(t):
    return (t.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

def rpr(color, sz=18, bold=False, italic=False):
    b = "<w:b/><w:bCs/>" if bold else ""
    i = "<w:i/><w:iCs/>" if italic else ""
    return (f"<w:rPr><w:rFonts w:ascii=\"Aptos\" w:hAnsi=\"Aptos\"/>"
            f"{b}{i}<w:color w:val=\"{color}\"/>"
            f"<w:sz w:val=\"{sz}\"/><w:szCs w:val=\"{sz}\"/></w:rPr>")

def run(text, color, sz=18, bold=False, italic=False):
    preserve = ' xml:space="preserve"' if text != text.strip() or text.startswith(" ") else ""
    return f"<w:r>{rpr(color,sz,bold,italic)}<w:t{preserve}>{esc(text)}</w:t></w:r>"

def make_para(fill, runs_xml, indent=None, sp_before=80, sp_after=40,
              border_top_color=None, para_rpr_color=None, para_rpr_sz=18, para_rpr_bold=False):
    pid = new_pid()
    border = ""
    if border_top_color:
        border = (f"<w:pBdr><w:top w:val=\"single\" w:sz=\"12\" w:space=\"1\" "
                  f"w:color=\"{border_top_color}\"/></w:pBdr>")
    shd  = f"<w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{fill}\"/>"
    sp   = f"<w:spacing w:before=\"{sp_before}\" w:after=\"{sp_after}\"/>"
    ind  = f"<w:ind w:left=\"180\"/>" if indent else ""
    # paragraph-level rPr (controls default run formatting inside pPr)
    p_rpr_xml = ""
    if para_rpr_color:
        p_rpr_xml = rpr(para_rpr_color, para_rpr_sz, para_rpr_bold)
        p_rpr_xml = f"<w:rPr>{p_rpr_xml[6:-7]}</w:rPr>"   # unwrap outer tag
    return (f"<w:p w14:paraId=\"{pid}\" w14:textId=\"77777777\" "
            f"w:rsidR=\"00CC0002\" w:rsidRDefault=\"00000000\">"
            f"<w:pPr>{border}{shd}{sp}{ind}{p_rpr_xml}</w:pPr>"
            f"{runs_xml}</w:p>")


# ── Block builders ────────────────────────────────────────────────────────────

def build_banner(sess_id, n_q):
    txt = f"  \u25a0  ITE SUPPLEMENT   \u2022   Session {sess_id:02d}   \u2022   {n_q} questions"
    return make_para(BANNER_FILL,
                     run(txt, "FFFFFF", sz=20, bold=True),
                     sp_before=200, sp_after=60,
                     border_top_color=BANNER_FILL)

def build_q_header(rank, qid, year, body_sys, subcat):
    txt = f"  Q{rank}   {qid}   \u2022   {year}   \u2022   {body_sys}   \u2022   {subcat}"
    return make_para(HEADER_FILL,
                     run(txt, "FFFFFF", sz=17, bold=True),
                     sp_before=80, sp_after=40)

def build_stem_row(text):
    # Wrap long stems — just emit as single paragraph, Word wraps automatically
    return make_para(BODY_FILL,
                     run("  " + text, "0D3D30", sz=18),
                     indent=True, sp_before=60, sp_after=20)

def build_choice_row(letter, text):
    label = run(f"  {letter})  ", "0D3D30", sz=18, bold=True)
    body  = run(text, "0D3D30", sz=18)
    return make_para(BODY_FILL, label + body,
                     indent=True, sp_before=20, sp_after=20)

def build_answer_row(letter, text):
    label   = run("  Answer:  ", "1B5E6E", sz=18, bold=True)
    answer  = run(f"{letter})  {text}", "1B5E6E", sz=18, bold=True)
    return make_para(ANSWER_FILL, label + answer,
                     indent=True, sp_before=60, sp_after=60)

def build_spacer():
    """Thin blank row between questions."""
    return make_para(BODY_FILL, "", sp_before=20, sp_after=20)


def build_session_block(sess_id, questions):
    """Build all XML paragraphs for one session's supplement block."""
    paras = [build_banner(sess_id, len(questions))]
    for rank, q in enumerate(questions, 1):
        paras.append(build_q_header(rank, q['question_id'], q['exam_year'],
                                    q['body_system'], q['subcategory']))
        paras.append(build_stem_row(q['question_text']))
        for c in q['choices']:
            paras.append(build_choice_row(c['letter'], c['text']))
        paras.append(build_answer_row(q['correct_letter'], q['correct_text']))
        if rank < len(questions):
            paras.append(build_spacer())
    return "\n".join(paras)

# ── Glossary builders ─────────────────────────────────────────────────────────

GLOSS_BANNER_FILL = "2E4057"   # dark navy — distinct from teal callouts
GLOSS_HEAD_FILL   = "3D5A7A"
GLOSS_SESS_FILL   = "4A6FA5"
GLOSS_BODY_FILL   = "EBF3FB"
GLOSS_ALT_FILL    = "D6E4F7"

def build_glossary_section(all_session_data):
    """Build the full end-of-document Answer Key & Explanations section."""
    paras = []

    # Section banner
    pid = new_pid()
    paras.append(make_para(GLOSS_BANNER_FILL,
                           run("  \u25a0  SUPPLEMENT ANSWER KEY & EXPLANATIONS",
                               "FFFFFF", sz=22, bold=True),
                           sp_before=300, sp_after=80,
                           border_top_color=GLOSS_BANNER_FILL))

    sub_txt = ("  All explanations and references are sourced from the ABFM ITE question bank "
               "(2020\u20132025). Organized by session.")
    paras.append(make_para(GLOSS_HEAD_FILL,
                           run(sub_txt, "FFFFFF", sz=16, italic=True),
                           sp_before=40, sp_after=60))

    for sess_id, sess_title, questions in all_session_data:
        # Session divider
        sess_hdr = f"  Session {sess_id:02d} \u2014 {sess_title}"
        paras.append(make_para(GLOSS_SESS_FILL,
                               run(sess_hdr, "FFFFFF", sz=18, bold=True),
                               sp_before=120, sp_after=40))

        for rank, q in enumerate(questions, 1):
            fill = GLOSS_BODY_FILL if rank % 2 == 1 else GLOSS_ALT_FILL

            # Q header line
            hdr = f"  Q{rank}  |  {q['question_id']}  |  {q['exam_year']}  |  {q['body_system']}  |  {q['subcategory']}"
            paras.append(make_para(fill,
                                   run(hdr, "1F3864", sz=16, bold=True),
                                   indent=True, sp_before=60, sp_after=20))

            # Answer line
            ans_txt = f"  Answer: {q['correct_letter']})  {q['correct_text']}"
            paras.append(make_para(fill,
                                   run(ans_txt, "1B5E6E", sz=17, bold=True),
                                   indent=True, sp_before=20, sp_after=20))

            # Explanation
            expl_label = run("  EXPLANATION  ", "333333", sz=16, bold=True)
            expl_body  = run(q['explanation'], "333333", sz=16)
            paras.append(make_para(fill, expl_label + expl_body,
                                   indent=True, sp_before=20, sp_after=20))

            # Reference (if present)
            if q.get('reference'):
                ref_label = run("  REFERENCE  ", "333333", sz=15, bold=True)
                ref_body  = run(q['reference'], "555555", sz=15, italic=True)
                paras.append(make_para(fill, ref_label + ref_body,
                                       indent=True, sp_before=10, sp_after=40))

    return "\n".join(paras)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # 1. Load clean question bank
    with open(Q_JSON, encoding='utf-8') as f:
        qs_list = json.load(f)
    qs = {q['question_id']: q for q in qs_list}
    print(f"Loaded {len(qs)} questions from clean bank")

    # 2. Load supplement assignments, build session -> [question_dicts]
    df_summary = pd.read_excel(SUPP_XLSX, sheet_name='Summary')
    session_questions = {}   # sess_id -> list of question dicts (ordered)
    session_titles    = {}   # sess_id -> title string

    for _, row in df_summary.iterrows():
        sess_label = str(row['Session'])
        parts = sess_label.split('\u2014', 1)
        sess_id    = int(parts[0].strip())
        sess_title = parts[1].strip() if len(parts) > 1 else sess_label
        session_titles[sess_id] = sess_title

        sheet = f'S{sess_id:02d}'
        df_sess = pd.read_excel(SUPP_XLSX, sheet_name=sheet)
        df_supp = df_sess[df_sess['Set'] == 'SUPPLEMENT'].reset_index(drop=True)

        q_list = []
        for _, qrow in df_supp.iterrows():
            qid = str(qrow['QID'])
            qid = SUBSTITUTE.get(qid, qid)   # swap garbled Q if needed
            if qid in qs and not qs[qid]['needs_review']:
                q_list.append(qs[qid])
            else:
                print(f"  WARNING: {qid} not ready for session {sess_id}, skipping")
        session_questions[sess_id] = q_list

    print(f"Session assignments loaded: {len(session_questions)} sessions")

    # 3. Load v5 docx XML
    shutil.copy2(SRC_DOCX, OUT_DOCX)
    with zipfile.ZipFile(OUT_DOCX, 'r') as z:
        xml = z.read('word/document.xml').decode('utf-8')
    print(f"Loaded v5 XML ({len(xml):,} chars)")

    # 4. Build session-order list and find injection anchors
    # Anchor: the text of each session heading paragraph
    # We insert the supplement block XML immediately BEFORE the next session heading
    # (or before </w:body> for the last session)

    sessions_sorted = sorted(session_questions.keys())

    # Find each session heading position in XML
    heading_positions = {}
    for sess_id in sessions_sorted:
        # Match "Session 02" or "Session 2:" style
        pattern = rf'Session\s+0?{sess_id}[.\s]'
        m = re.search(pattern, xml)
        if m:
            heading_positions[sess_id] = m.start()
        else:
            print(f"  WARNING: Could not find heading for Session {sess_id}")

    print(f"Found {len(heading_positions)} session headings")

    # 5. Build all supplement blocks and inject — work backwards to preserve positions
    modified_xml = xml

    for sess_id in reversed(sessions_sorted):
        if sess_id not in heading_positions:
            continue
        questions = session_questions.get(sess_id, [])
        if not questions:
            continue

        block_xml = build_session_block(sess_id, questions)

        # Find where THIS session ends = start of next session's heading paragraph
        # We insert block right before that <w:p> containing next heading
        if sess_id == sessions_sorted[-1]:
            # Last session: insert before </w:body>
            insert_marker = '</w:body>'
            modified_xml = modified_xml.replace(insert_marker,
                                                 block_xml + "\n" + insert_marker, 1)
        else:
            next_id = sessions_sorted[sessions_sorted.index(sess_id) + 1]
            if next_id not in heading_positions:
                continue
            # Find the <w:p ...> that contains the next session heading
            next_heading_txt_pattern = rf'Session\s+0?{next_id}[.\s]'
            m_next = re.search(next_heading_txt_pattern, modified_xml)
            if not m_next:
                print(f"  WARNING: Lost heading for Session {next_id} after edits")
                continue
            # Walk back to find the opening <w:p of that paragraph
            para_open = modified_xml.rfind('<w:p ', 0, m_next.start())
            if para_open == -1:
                print(f"  WARNING: Could not find <w:p for Session {next_id}")
                continue
            modified_xml = (modified_xml[:para_open] +
                            block_xml + "\n" +
                            modified_xml[para_open:])

        print(f"  Injected Session {sess_id:02d} ({len(questions)} questions)")

    # 6. Build and append glossary before </w:body>
    print("\nBuilding end-of-document glossary...")
    all_session_data = []
    for sess_id in sessions_sorted:
        title   = session_titles.get(sess_id, f"Session {sess_id:02d}")
        q_list  = session_questions.get(sess_id, [])
        if q_list:
            all_session_data.append((sess_id, title, q_list))

    glossary_xml = build_glossary_section(all_session_data)
    modified_xml = modified_xml.replace('</w:body>',
                                        glossary_xml + "\n</w:body>", 1)
    print(f"Glossary appended ({len(all_session_data)} sessions, "
          f"{sum(len(x[2]) for x in all_session_data)} entries)")

    # 7. Write modified XML back into docx
    tmp = OUT_DOCX + ".tmp"
    with zipfile.ZipFile(OUT_DOCX, 'r') as zin:
        with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'word/document.xml':
                    zout.writestr(item, modified_xml.encode('utf-8'))
                else:
                    zout.writestr(item, zin.read(item.filename))
    os.replace(tmp, OUT_DOCX)
    print(f"\nDone: {OUT_DOCX}")
    print(f"Final XML size: {len(modified_xml):,} chars")


if __name__ == '__main__':
    main()
