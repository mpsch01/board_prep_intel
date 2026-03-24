import sys, os, winreg
print("Python:", sys.version)

# Check process env
api_key = os.environ.get('ANTHROPIC_API_KEY', '')
print("ANTHROPIC_API_KEY in process env:", bool(api_key))

# Check user-level env var in registry
try:
    reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
    val, _ = winreg.QueryValueEx(reg, "ANTHROPIC_API_KEY")
    print("ANTHROPIC_API_KEY in user registry: YES, length:", len(val))
    winreg.CloseKey(reg)
except Exception as e:
    print("ANTHROPIC_API_KEY in user registry: NOT FOUND -", e)

# Check system-level
try:
    reg2 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
    val2, _ = winreg.QueryValueEx(reg2, "ANTHROPIC_API_KEY")
    print("ANTHROPIC_API_KEY in system registry: YES, length:", len(val2))
    winreg.CloseKey(reg2)
except Exception as e:
    print("ANTHROPIC_API_KEY in system registry: NOT FOUND -", e)
