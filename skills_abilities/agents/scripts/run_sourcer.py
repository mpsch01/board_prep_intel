"""
Launcher wrapper for pdf_sourcer_agent.py
Reads ANTHROPIC_API_KEY from Windows user registry and injects into env,
then runs the sourcer with the specified arguments.
"""
import os, sys, winreg, subprocess

# --- Read API key from user registry ---
try:
    reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
    api_key, _ = winreg.QueryValueEx(reg, "ANTHROPIC_API_KEY")
    winreg.CloseKey(reg)
    print(f"[launcher] API key loaded from registry (length={len(api_key)})")
except Exception as e:
    print(f"[launcher] ERROR: Could not read ANTHROPIC_API_KEY from registry: {e}")
    sys.exit(1)

# --- Inject into env ---
env = os.environ.copy()
env["ANTHROPIC_API_KEY"] = api_key
env["PYTHONIOENCODING"] = "utf-8"   # fix Windows cp1252 unicode crash

# --- Build command ---
python_exe = sys.executable
script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_sourcer_agent.py")
args = sys.argv[1:]  # pass-through all arguments

cmd = [python_exe, script] + args
print(f"[launcher] Running: {' '.join(cmd)}")
print("[launcher] " + "="*60)

# --- Run ---
result = subprocess.run(cmd, env=env)
sys.exit(result.returncode)
