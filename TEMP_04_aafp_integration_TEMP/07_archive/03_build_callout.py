
def build_callout(sess):
    """Build the full XML block to insert after a session heading."""
    tier   = sess['session_tier']
    colors = TIER_COLORS[tier]
    hdr    = colors['header']
    lt     = colors['light']
    label  = colors['label']

    snum   = sess['session_number']
    sname  = sess['session_name']
    score  = sess['best_yield_score']
    subcats= sess.get('tier1_subcategories', []) + sess.get('tier2_subcategories', [])
    subcats_str = ', '.join(subcats[:3]) if subcats else 'General Review'

    top_sub = sess.get('top_subcategory', {})
    total_qs= top_sub.get('total_qs_6yr', '—')
    avg_q   = top_sub.get('avg_per_exam', '—')
    trend   = top_sub.get('trend', '—')

    # ── Table XML ──────────────────────────────────────────────────────
    # Header row
    header_text = f'{label}   |   Session {snum}: {sname}   |   Score: {score:.2f}'
    rows = [table_row_1col(header_text, fill=hdr, text_color='FFFFFF', bold=True, size=20)]

    # Stats row
    col1 = f'ITE Questions (6yr): {total_qs}  |  Avg/Exam: {avg_q}'
    col2 = f'Trend: {trend}'
    col3 = f'Top Topics: {subcats_str}'
    rows.append(table_row_3col(col1, col2, col3, fill=lt))

    # ITE Questions section
    ite_qs = sess.get('top_questions', [])[:MAX_ITE_QS]
    if ite_qs:
        rows.append(table_row_1col('ITE EXAM QUESTIONS', fill=hdr, text_color='FFFFFF', bold=True, size=17))
        for i, q in enumerate(ite_qs, 1):
            yr  = q.get('exam_year', '?')
            qid = q.get('question_id', '')
            clust = q.get('cluster', '')
            mr  = ' [MUST-READ REF]' if q.get('is_must_read_ref') else ''
            c1 = f'Q{i}  ({yr})'
            c2 = f'{clust}'
            c3 = f'ID: {qid}{mr}'
            rows.append(table_row_3col(c1, c2, c3, fill='FFFFFF'))

    # Must-read refs section
    refs = sess.get('must_read_refs', [])[:MAX_REFS]
    if refs:
        rows.append(table_row_1col('MUST-READ REFERENCES', fill=hdr, text_color='FFFFFF', bold=True, size=17))
        for ref in refs:
            cite = ref.get('citation', '')[:120]
            cnt  = ref.get('citation_count', '')
            yrs  = ref.get('unique_years', '')
            c1 = cite
            c2 = f'Cited: {cnt}x'
            c3 = f'Years: {yrs}'
            rows.append(table_row_3col(c1, c2, c3, fill='FFFFFF'))

    # Poll questions section
    polls = sess.get('poll_questions', [])[:MAX_POLL_QS]
    if polls:
        rows.append(table_row_1col('PRESENTER POLL QUESTIONS', fill=hdr, text_color='FFFFFF', bold=True, size=17))
        for pq in polls:
            stem = str(pq.get('stem', ''))[:140]
            subcat = str(pq.get('matched_subcat', ''))
            c1 = stem
            c2 = subcat
            c3 = f"A: {pq.get('choice_A','')[:40]}"
            rows.append(table_row_3col(c1, c2, c3, fill='FFFFFF'))

    # Assemble table
    tid = rand_id()
    table_xml = (
        f'<w:tbl>'
        f'<w:tblPr>'
        f'<w:tblStyle w:val="TableGrid"/>'
        f'<w:tblW w:w="9360" w:type="dxa"/>'
        f'<w:tblInd w:w="0" w:type="dxa"/>'
        f'<w:tblBorders>'
        f'<w:top w:val="single" w:sz="6" w:color="{hdr}"/>'
        f'<w:left w:val="single" w:sz="6" w:color="{hdr}"/>'
        f'<w:bottom w:val="single" w:sz="6" w:color="{hdr}"/>'
        f'<w:right w:val="single" w:sz="6" w:color="{hdr}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:color="AAAAAA"/>'
        f'<w:insideV w:val="single" w:sz="4" w:color="AAAAAA"/>'
        f'</w:tblBorders>'
        f'<w:tblCellMar>'
        f'<w:top w:w="60" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        f'<w:bottom w:w="60" w:type="dxa"/><w:right w:w="120" w:type="dxa"/>'
        f'</w:tblCellMar>'
        f'</w:tblPr>'
        f'<w:tblGrid><w:gridCol w:w="3120"/><w:gridCol w:w="3120"/><w:gridCol w:w="3120"/></w:tblGrid>'
        + ''.join(rows) +
        f'</w:tbl>'
    )

    # Spacer paragraph before and after
    spacer = para('', space_before=60, space_after=60)
    return spacer + table_xml + spacer
