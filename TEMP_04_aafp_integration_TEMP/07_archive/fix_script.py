content = open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\updated_data_docs\build_excel.py', encoding='utf-8').read()
old = "hdr(ws3, delta_start+1, 1, '\u25b2 RISING (2025 vs 2020)', bg=GREEN, fg=NAVY, span=5)\nws3.merge_cells(start_row=delta_start+1, start_column=1, end_row=delta_start+1, end_column=5)"
new = "ws3.merge_cells(start_row=delta_start+1, start_column=1, end_row=delta_start+1, end_column=5)\nhdr(ws3, delta_start+1, 1, '\u25b2 RISING (2025 vs 2020)', bg=GREEN, fg=NAVY)"
content = content.replace(old, new)
open(r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\01_source\updated_data_docs\build_excel.py', 'w', encoding='utf-8').write(content)
print('done')
