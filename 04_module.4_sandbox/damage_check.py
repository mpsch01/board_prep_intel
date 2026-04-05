from pathlib import Path

base = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\citation_files\ITE')
tiers = ['VC_fail', 'VC_pass', 'local_lite', 'right_click']

lines = []
total = 0
for t in tiers:
    d = base / t
    if d.exists():
        count = len(list(d.glob('*.pdf')))
        total += count
        lines.append(f'{t}={count}')
    else:
        lines.append(f'{t}=FOLDER_MISSING')

lines.append(f'TOTAL={total}')

# Also check scripts folder
scripts_dir = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\scripts')
lines.append(f'scripts_exists={scripts_dir.exists()}')

ite_exams = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\ite_exams')
lines.append(f'ite_exams_pdf_count={len(list(ite_exams.glob("*.pdf")))}')

output = '\n'.join(lines)
out_path = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\04_module.4_sandbox\damage_check.txt')
out_path.write_text(output)
print(output)
