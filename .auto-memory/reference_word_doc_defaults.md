---
name: Word Doc Defaults Template
description: word_doc_defaults.py — St. Luke's/ITE color scheme + Aptos font. Import this module in any python-docx build script for this project.
type: reference
---

## File Location
`03_module.3_analyst/scripts/word_doc_defaults.py`

## Rule
**Any Word document built for this project must import and apply these defaults.**
`from word_doc_defaults import *`

## Color Palette (St. Luke's — dark navy / gold / medium blue)
| Name | Hex | Use |
|------|-----|-----|
| NAVY | `1B3564` | Titles, headers, section labels |
| GOLD | `C8922A` | Left border bars, highlights |
| BLUE | `2E5F9C` | Subheaders, labels |
| LIGHT_BLUE | `EBF0F7` | Answer boxes, shaded cells |
| DARK_TEXT | `1A1A2E` | Body text (near-black) |
| MED_GRAY | `808080` | Secondary text, footers, captions |
| GREEN | `(62, 141, 39)` | Correct-answer green — RGBColor(*GREEN) |

## Typography
- **Font:** Aptos (all elements)
- Title: 26pt bold navy
- Subtitle: 14pt blue
- Heading: 12pt bold navy (level 1) / 11pt bold blue (level 2)
- Body: 11pt dark text
- Small: 10pt
- Tiny: 9pt (footers)

## Page Setup
- US Letter (8.5" × 11"), 1" margins all sides

## Key Helper Functions
| Function | Purpose |
|----------|---------|
| `new_document()` | Returns a Document with page setup + default font applied |
| `add_title(doc, text)` | 26pt bold navy, centered, navy rule below |
| `add_subtitle(doc, text)` | 14pt blue, centered |
| `add_section_header(doc, text, level=1)` | Gold left border + light blue bg; level 1 = navy, level 2 = blue |
| `add_body_text(doc, text, indent=0.25)` | 11pt dark text, left indent |
| `add_divider(doc)` | Thin gray horizontal rule |
| `add_page_number_footer(doc_section)` | Left: "2025 ABFM ITE \| St. Luke's Family Medicine Residency" + right-aligned page number |
| `add_shading(para, fill_color)` | Background fill by hex string |
| `add_left_border(para, color=GOLD, size=24)` | Thick gold vertical left bar |
| `add_bottom_border(para, color, size)` | Thin horizontal rule below paragraph |
| `sanitize(text)` | Fix Windows-1252 mojibake (combines fix_encoding + clean_text) |

## Footer Text (hardcoded)
`"2025 ABFM ITE  |  St. Luke's Family Medicine Residency"` — left-aligned, page number tab-right
