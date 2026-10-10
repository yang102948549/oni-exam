"""Hancom render with cleanup + retry: render_retry.py file.hwpx  -> file.pdf"""
import subprocess, sys, time
from pathlib import Path
f = Path(sys.argv[1]); pdf = f.with_suffix('.pdf')
for attempt in range(int(sys.argv[2]) if len(sys.argv) > 2 else 4):
    subprocess.run(['taskkill', '/F', '/IM', 'Hwp.exe'], capture_output=True); time.sleep(2)
    pdf.unlink(missing_ok=True)
    try:
        subprocess.run([sys.executable, str(Path(__file__).with_name('render_hwpx_hancom.py')), str(f), '--pdf', str(pdf)],
                       timeout=45, capture_output=True)
    except subprocess.TimeoutExpired:
        pass
    if pdf.exists(): break
subprocess.run(['taskkill', '/F', '/IM', 'Hwp.exe'], capture_output=True)
print(pdf.name, 'ok' if pdf.exists() else 'FAILED', 'attempts', attempt + 1)
