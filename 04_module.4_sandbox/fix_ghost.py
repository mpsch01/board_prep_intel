"""
fix_ghost.py - Verify and clean up the ghost folder
Checks that all remaining ghost files exist at correct destination,
then removes the duplicates and the ghost folder structure.
"""
from pathlib import Path
import shutil

GHOST_BASE = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\01_module.1_warehouse\citation_files\ITE')
DEST_BASE  = Path(r'C:\Users\mpsch\Desktop\board_prep_intel\01_module.1_warehouse\citation_files\ITE')

print("=== Checking ghost folder contents ===")
print(f"Ghost: {GHOST_BASE}")
print(f"Dest:  {DEST_BASE}")
print()

all_clear = True
ghost_files = []

for tier_dir in sorted(GHOST_BASE.iterdir()):
    if not tier_dir.is_dir():
        continue
    dest_tier = DEST_BASE / tier_dir.name
    print(f"--- {tier_dir.name} ---")
    for f in sorted(tier_dir.iterdir()):
        if not f.is_file():
            continue
        dest_f = dest_tier / f.name
        exists = dest_f.exists()
        status = "[OK at dest]" if exists else "[MISSING FROM DEST]"
        print(f"  {f.name} {status}")
        ghost_files.append((f, dest_f, exists))
        if not exists:
            all_clear = False

print()
print(f"Total ghost files remaining: {len(ghost_files)}")
safe_to_delete = [g for g, d, exists in ghost_files if exists]
missing_at_dest = [(g, d) for g, d, exists in ghost_files if not exists]

print(f"  Safe to delete (already at dest): {len(safe_to_delete)}")
print(f"  NOT at dest yet (need to move):   {len(missing_at_dest)}")

if missing_at_dest:
    print("\nMoving files not yet at destination...")
    for ghost_f, dest_f in missing_at_dest:
        dest_f.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ghost_f), str(dest_f))
        print(f"  MOVED: {ghost_f.name} -> {dest_f.parent.name}/")

print("\nDeleting ghost duplicates...")
for ghost_f, dest_f, exists in ghost_files:
    if ghost_f.exists():
        ghost_f.unlink()
        print(f"  DELETED: {ghost_f.name}")

# Clean up empty directories in ghost folder
print("\nRemoving empty ghost directories...")
for d in sorted(GHOST_BASE.rglob('*'), reverse=True):
    if d.is_dir():
        try:
            d.rmdir()
            print(f"  REMOVED dir: {d}")
        except OSError:
            print(f"  KEPT (not empty): {d}")

# Try to remove the ghost base dirs
ghost_root = GHOST_BASE.parent.parent.parent  # 01_module.1_warehouse/01_module.1_warehouse
print(f"\nAttempting to remove ghost root: {ghost_root}")
try:
    shutil.rmtree(str(ghost_root))
    print("  Ghost folder tree DELETED.")
except Exception as e:
    print(f"  Could not auto-delete: {e}")
    print("  Remaining files in ghost root:")
    for f in sorted(ghost_root.rglob('*')):
        print(f"    {f}")

print("\nDone.")
