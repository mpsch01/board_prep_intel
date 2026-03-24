import time, subprocess
t = time.time()
subprocess.run(['py', '-3.12', 'main.py', '--dir', 'documents/timing_test/', '--out', 'outputs/timing_test/'])
elapsed = time.time() - t
print(f"\nTOTAL WALL TIME: {elapsed/60:.1f} min  ({elapsed:.0f} sec)")
