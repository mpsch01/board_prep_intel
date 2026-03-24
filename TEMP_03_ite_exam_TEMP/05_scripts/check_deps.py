import sys
print("Python:", sys.version)
try:
    import docx
    print("python-docx: OK", docx.__version__)
except ImportError as e:
    print("python-docx: MISSING -", e)
try:
    import pandas as pd
    print("pandas: OK", pd.__version__)
except ImportError as e:
    print("pandas: MISSING -", e)
