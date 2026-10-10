"""Render several HWPX files to PDF in one Hancom session: render_many.py a.hwpx b.hwpx ... (PDF next to each)."""
import sys, win32com.client
from pathlib import Path
h = win32com.client.DispatchEx('HWPFrame.HwpObject'); h.XHwpWindows.Item(0).Visible = True
try:
    for f in sys.argv[1:]:
        f = Path(f).resolve(); pdf = f.with_suffix('.pdf')
        ok = h.Open(str(f), 'HWPX', 'forceopen:true'); pages = h.PageCount
        print(f.name, 'open', ok, 'pages', pages, 'pdf', h.SaveAs(str(pdf), 'PDF', ''), flush=True)
        h.Clear(1)
finally:
    h.Quit()
