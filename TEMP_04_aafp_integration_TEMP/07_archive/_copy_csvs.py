import shutil, os

# Try Downloads first, then Desktop
for src_dir in [
    r'C:\Users\mpsch\Downloads',
    r'C:\Users\mpsch\Desktop',
    r'C:\Users\mpsch\Desktop\claude_knowledge'
]:
    for fname in ['poll_questions_raw.csv', 'poll_questions_tagged.csv']:
        src = os.path.join(src_dir, fname)
        if os.path.exists(src):
            dst = rf'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\03_poll_questions\{fname}'
            shutil.copy(src, dst)
            print(f'Copied: {src} -> {dst}')

# Also check if they're already there
dst_dir = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\03_poll_questions'
print('Files in 03_poll_questions:', os.listdir(dst_dir))
