"""Open a generated HWPX in a dedicated Hancom instance and export PDF."""
from pathlib import Path
import argparse,win32com.client
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--pdf',required=True);args=p.parse_args()
h=win32com.client.DispatchEx('HWPFrame.HwpObject');h.XHwpWindows.Item(0).Visible=True
try: print('SECURITY_MODULE',h.RegisterModule('FilePathCheckDLL','SecurityModule'),flush=True)  # 사용자가 레지스트리에 모듈을 등록해 둔 경우에만 True
except Exception as e: print('SECURITY_MODULE',e,flush=True)
try:
 print('OPEN',h.Open(str(Path(args.input).resolve()),'HWPX','forceopen:true'),flush=True)
 print('PAGES',h.PageCount,flush=True)
 print('PDF',h.SaveAs(str(Path(args.pdf).resolve()),'PDF',''),flush=True)
 print('TEXT',len(h.GetTextFile('TEXT','')),flush=True)
finally:h.Quit()
