"""
Injects SESSION Heading1 paragraphs directly into document.xml XML.
- Uses ElementTree to parse/manipulate
- Inserts proper Heading1 styled paragraphs
- Reorders interleaved Geriatrics blocks (18 and 19 are non-contiguous in the source)
- Adds placeholder paragraphs for Sessions 33 and 34 (no outline content exists)
"""

import xml.etree.ElementTree as ET
import copy, re

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W14 = 'http://schemas.microsoft.com/office/word/2010/wordml'

# Register all namespaces from the file to preserve them
namespaces_raw = {}
for event, elem in ET.iterparse('/home/claude/unpacked/word/document.xml', events=['start-ns']):
    namespaces_raw[elem[0]] = elem[1]
for prefix, uri in namespaces_raw.items():
    ET.register_namespace(prefix, uri)

tree = ET.parse('/home/claude/unpacked/word/document.xml')
root = tree.getroot()
body = root.find(f'{{{W}}}body')
children = list(body)

def get_style(para):
    pPr = para.find(f'{{{W}}}pPr')
    if pPr is None: return None
    pStyle = pPr.find(f'{{{W}}}pStyle')
    if pStyle is None: return None
    return pStyle.get(f'{{{W}}}val')

def get_text(para):
    return ''.join(r.text or '' for r in para.findall(f'.//{{{W}}}t'))

# ── Build a Heading1 paragraph element ──────────────────────────────────────
_para_counter = [0x1000]
def make_heading1(text, rsid='00AA1234'):
    """Create a w:p with Heading1 style containing the given text."""
    _para_counter[0] += 1
    pid = f'{_para_counter[0]:08X}'
    p = ET.Element(f'{{{W}}}p')
    p.set(f'{{{W14}}}paraId', pid)
    p.set(f'{{{W14}}}textId', '77777777')
    p.set(f'{{{W}}}rsidR', rsid)
    p.set(f'{{{W}}}rsidRDefault', rsid)
    pPr = ET.SubElement(p, f'{{{W}}}pPr')
    pStyle = ET.SubElement(pPr, f'{{{W}}}pStyle')
    pStyle.set(f'{{{W}}}val', 'Heading1')
    r = ET.SubElement(p, f'{{{W}}}r')
    t = ET.SubElement(r, f'{{{W}}}t')
    t.text = text
    return p

def make_placeholder(session_num, text, note):
    """Heading1 for session + a Normal paragraph with the note."""
    h = make_heading1(text)
    p = ET.Element(f'{{{W}}}p')
    pPr = ET.SubElement(p, f'{{{W}}}pPr')
    # italic note paragraph
    r = ET.SubElement(p, f'{{{W}}}r')
    rPr = ET.SubElement(r, f'{{{W}}}rPr')
    i = ET.SubElement(rPr, f'{{{W}}}i')
    t = ET.SubElement(r, f'{{{W}}}t')
    t.text = note
    return [h, p]

# ── Find all Style1 body indices ─────────────────────────────────────────────
style1_indices = []
for i, child in enumerate(children):
    if child.tag == f'{{{W}}}p' and get_style(child) == 'Style1':
        style1_indices.append(i)

# Map position in style1_indices list → the paragraph element
# style1_indices[0]=body_idx 82 → "02. PERIPHERAL VASCULAR DISEASE..."
# (Matches the output from the analysis above)

# Session → list of style1_indices[] positions to include (0-based into style1_indices)
session_style1_positions = {
    2:  [0],
    3:  [1],
    4:  [2],
    5:  [3],
    6:  [4],
    7:  [5],
    8:  [6],
    9:  [7],
    10: [8],
    11: [9],
    12: [10, 11, 12],   # Trauma + Surgical Abdomen + ID/Allergy/Tox
    13: [13],
    14: [14],
    15: [15],
    16: [16],
    17: [17],
    # Geriatrics: non-contiguous — reordered
    18: [18, 20],       # Systems of Care (18) + Capacity/Ethics (20)
    19: [19, 21],       # Osteoporosis (19) + Urology/Endocrine (21)
    20: [22, 23],       # Pharmacology (22) + Disease-Specific (23)
    21: [24, 25, 26],   # All 3 hematology blocks
    22: [27],
    23: [28, 29],       # STIs + Viral Hepatitis
    24: [30, 31],
    25: [32, 33],
    26: [34, 35, 36],   # Seizures + Headache + MS
    27: [37, 38],
    28: [39, 40],
    29: [41, 42, 43],   # AUB + Menopause + Gyn Onc
    30: [44, 45],       # Breast + Contraception
    31: [46],
    32: [47],
    33: [],             # PLACEHOLDER — no outline section
    34: [],             # PLACEHOLDER — no outline section
    35: [48, 49, 50],   # 3 ENT blocks
    36: [51, 52],
    37: [53, 54],
    38: [55, 56],
    39: [57],
    40: [58, 59],       # Bipolar/Anxiety + Personality Disorders
    41: [60, 61, 62],   # ADHD + ASD + OCD
    42: [63],
    43: [64],
    44: [65, 66],
    45: [67, 68],
    46: [69],
    47: [70],
    48: [71],
    49: [72],
}

session_titles = {
    2:  "Session 02: Peripheral Vascular Disease",
    3:  "Session 03: Acute Coronary Syndrome (ACS) & Hyperlipidemia",
    4:  "Session 04: Hypertension",
    5:  "Session 05: Heart Failure",
    6:  "Session 06: Managing Dysrhythmias",
    7:  "Session 07: Health Promotion & Prevention",
    8:  "Session 08: Epidemiology & Medical Literature",
    9:  "Session 09: Managing Common Cutaneous Problems",
    10: "Session 10: Emergency Medicine I",
    11: "Session 11: Emergency Medicine II",
    12: "Session 12: Emergency Medicine III",
    13: "Session 13: Obesity & Metabolic Syndrome",
    14: "Session 14: Diabetes Mellitus",
    15: "Session 15: Endocrine Diseases",
    16: "Session 16: Lower GI Tract Diseases",
    17: "Session 17: Upper GI Tract Diseases",
    18: "Session 18: Geriatrics I \u2014 Systems of Care & Cognitive Impairment",
    19: "Session 19: Geriatrics II \u2014 Osteoporosis, Gait & Prevention",
    20: "Session 20: Geriatrics III \u2014 Pharmacokinetics & Polypharmacy",
    21: "Session 21: Hematology Issues",
    22: "Session 22: Fever & Infectious Disease in Children",
    23: "Session 23: STIs, Vaginitis & Vaginosis",
    24: "Session 24: Renal Disease I",
    25: "Session 25: Renal Disease II",
    26: "Session 26: Common Neurological Disorders",
    27: "Session 27: Maternity Care I \u2014 Prenatal Care & Early Complications",
    28: "Session 28: Maternity Care II \u2014 Medical Complications & Labor Management",
    29: "Session 29: Women\u2019s Health I \u2014 AUB & Gynecologic Oncology",
    30: "Session 30: Women\u2019s Health II \u2014 Breast Issues, Contraception & Infertility",
    31: "Session 31: Musculoskeletal Medicine",
    32: "Session 32: Fracture Care",
    33: "Session 33: Sports Medicine",
    34: "Session 34: Pediatric Orthopedics",
    35: "Session 35: Common ENT Problems",
    36: "Session 36: Management of Chronic Pain",
    37: "Session 37: Common Newborn Issues",
    38: "Session 38: Well-Child & Adolescent Issues",
    39: "Session 39: Behavioral Medicine I \u2014 Depression",
    40: "Session 40: Behavioral Medicine II \u2014 Bipolar & Anxiety Disorders",
    41: "Session 41: Behavioral Medicine III \u2014 ADHD, Autism & OCD",
    42: "Session 42: Pulmonary I \u2014 COPD",
    43: "Session 43: Pulmonary II \u2014 Asthma",
    44: "Session 44: Pulmonary III \u2014 Pulmonary Infections & Pneumonia Part 1",
    45: "Session 45: Pulmonary IV \u2014 Infections, Pneumonia Part 2 & Occupational Lung Disease",
    46: "Session 46: Pulmonary V \u2014 Lung Cancer, OSA, Sarcoidosis & Pulmonary Fibrosis",
    47: "Session 47: The Major Arthritides",
    48: "Session 48: Preoperative Examination & Management",
    49: "Session 49: Urologic Problems",
}

placeholders = {
    33: "No dedicated section found in this outline document. Sports Medicine content is covered in Session 33 slides (33-SLIDES_sports-medicine.pdf) and transcript (33-sports-medicine.txt). Review those sources to add content here.",
    34: "No dedicated section found in this outline document. Pediatric Orthopedics content is covered in Session 34 slides and transcript. Note: Session 32 (Fracture Care) above contains some pediatric fracture content (Salter-Harris classification, nursemaid\u2019s elbow) which may overlap.",
}

# ── Rebuild body children in the correct order ───────────────────────────────
# Strategy:
#   1. Keep all non-Style1 paragraphs in their original body positions
#      up to the first Style1 block.
#   2. For each session, emit: session heading + all paragraphs up to
#      (but not including) the next Style1 block.
#   3. For Geriatrics (sessions 18-19) where blocks are non-contiguous,
#      collect all blocks belonging to the session before moving on.

# Build a lookup: body_index → session it belongs to (for each Style1 para)
# and which paragraphs follow it (up to next Style1)
def get_block_paragraphs(style1_pos_in_list, children):
    """Return the Style1 para + all following paras up to but not including next Style1."""
    start_body_idx = style1_indices[style1_pos_in_list]
    if style1_pos_in_list + 1 < len(style1_indices):
        end_body_idx = style1_indices[style1_pos_in_list + 1]
    else:
        # Last block: go to sectPr (last element in body)
        end_body_idx = len(children) - 1  # exclude sectPr
    return children[start_body_idx:end_body_idx]

# Preamble: everything before the first Style1 paragraph
preamble = children[:style1_indices[0]]

# Build the set of all body indices that are "claimed" by a session
# (so we can skip them when we hit them out of order for geriatrics)
claimed = set()
for sess, positions in session_style1_positions.items():
    for pos in positions:
        claimed.add(pos)

# Build output
new_children = list(preamble)

for sess in range(2, 50):
    positions = session_style1_positions.get(sess, [])
    
    # Session heading
    new_children.append(make_heading1(session_titles[sess]))
    
    if not positions:
        # Placeholder sessions (33, 34)
        note_p = ET.Element(f'{{{W}}}p')
        r = ET.SubElement(note_p, f'{{{W}}}r')
        rPr = ET.SubElement(r, f'{{{W}}}rPr')
        ET.SubElement(rPr, f'{{{W}}}i')  # italic
        t = ET.SubElement(r, f'{{{W}}}t')
        t.text = placeholders[sess]
        new_children.append(note_p)
    else:
        for pos in positions:
            block = get_block_paragraphs(pos, children)
            new_children.extend(block)

# Append sectPr (last element — page/section properties, must be last)
new_children.append(children[-1])

# Replace body children
for child in list(body):
    body.remove(child)
for child in new_children:
    body.append(child)

# Write back
tree.write('/home/claude/unpacked/word/document.xml',
           xml_declaration=True, encoding='UTF-8')

print(f"Done. Body now has {len(list(body))} children.")
print("Heading1 paragraphs inserted:")
count = 0
for child in body:
    if child.tag == f'{{{W}}}p' and get_style(child) == 'Heading1':
        count += 1
        print(f"  {get_text(child)[:70]}")
print(f"Total: {count}")
