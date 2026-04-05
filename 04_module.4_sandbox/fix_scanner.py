import shutil
from pathlib import Path

GHOST = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\01_module.1_warehouse\citation_files\ITE')
DEST  = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\citation_files\ITE')

moved = 0
for tier_folder in ['VC_fail', 'VC_pass']:
    src_dir = GHOST / tier_folder
    dst_dir = DEST / tier_folder
    dst_dir.mkdir(parents=True, exist_ok=True)
    for pdf in src_dir.glob('*.pdf'):
        dest_file = dst_dir / pdf.name
        if dest_file.exists():
            print(f'  SKIP (already exists): {pdf.name}')
        else:
            shutil.move(str(pdf), str(dest_file))
            print(f'  MOVED [{tier_folder}]: {pdf.name}')
            moved += 1

print(f'\nDone. {moved} files moved.')
print('Ghost folder still exists (empty) — you can delete it manually via Explorer.')
