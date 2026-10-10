"""쪽 수가 원본과 같아지는 가장 큰 여백 비율(prevk)을 이분 탐색한다.
usage: python -X utf8 scripts/fit_pages.py ITEMS.json OUT.hwpx -- <build args...>
"""
import json, subprocess, sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parent.parent
items, out = Path(sys.argv[1]), Path(sys.argv[2]); bargs = sys.argv[sys.argv.index('--') + 1:]
want = len({b['page'] for b in json.loads(items.read_text(encoding='utf-8'))})
def trial(k):
    subprocess.run(['taskkill', '/F', '/IM', 'Hwp.exe'], capture_output=True)
    subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/build_hwpx_doc4.py'), '--items', str(items), '--out', str(out), '--prevk', str(k)] + bargs, check=True, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/render_retry.py'), str(out), '3'], capture_output=True)
    return len(pymupdf.open(str(out.with_suffix('.pdf'))))
lo, hi = 0.0, 1.0; best = None
n = trial(1.0); print('prevk 1.00 ->', n, 'pages (want', want, ')', flush=True)
if n == want: best = 1.0
else:
    for _ in range(6):
        mid = round((lo + hi) / 2, 3); n = trial(mid); print('prevk', mid, '->', n, flush=True)
        if n <= want: best, lo = mid, mid
        else: hi = mid
    if best is not None: trial(best)
print('best prevk:', best)
