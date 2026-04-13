# download_targeted.py — one-off script to grab specific failing URLs
# with domain-specific Referer headers. Downloads to user's Downloads folder.
import requests, time
from pathlib import Path

DEST = Path.home() / "Downloads"  # resolves to current user's Downloads folder

# Remaining fixable failures only
targets = [
    # WHO — append ?sequence=1&isAllowed=y to force direct PDF serve
    ('ART-0170', 'https://iris.who.int/bitstream/handle/10665/348546/WHO-HEP-NFS-21.45-eng.pdf?sequence=1&isAllowed=y', 'iris.who.int', False),
    ('ART-0200', 'https://iris.who.int/bitstream/handle/10665/349321/WHO-2019-nCoV-clinical-2021.2-eng.pdf?sequence=1&isAllowed=y', 'iris.who.int', False),
    # VA — verify=False (DoD CA not in Python bundle)
    ('ART-1277', 'https://healthquality.va.gov/guidelines/MH/ptsd/VADoDPTSDCPGFinal.pdf', 'healthquality.va.gov', False),
    ('ART-1863', 'https://www.healthquality.va.gov/guidelines/MH/ptsd/VADoDPTSDCPGFinal012418.pdf', 'healthquality.va.gov', False),
]

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ok, fail = 0, 0
for art_id, url, referer, verify in targets:
    h = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': f'https://{referer}/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
    try:
        r = requests.get(url, headers=h, timeout=30, stream=True,
                         allow_redirects=True, verify=verify)
        ct = r.headers.get('Content-Type', '')
        first = next(r.iter_content(8), b'')
        is_pdf = 'pdf' in ct or first.startswith(b'%PDF')
        if r.status_code == 200 and is_pdf:
            fname = url.split('/')[-1].split('?')[0] or f'{art_id}.pdf'
            dest = DEST / fname
            with open(dest, 'wb') as f:
                f.write(first)
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            print(f'OK   {art_id} -> {fname}')
            ok += 1
        else:
            print(f'FAIL {art_id} -> HTTP {r.status_code} | {ct[:50]}')
            fail += 1
    except Exception as e:
        print(f'ERR  {art_id} -> {e}')
        fail += 1
    time.sleep(1.5)

print(f'\nDone: {ok} downloaded, {fail} failed')
