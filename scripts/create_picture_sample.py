from pathlib import Path
import win32com.client
root=Path('output/korean_exam_test').resolve()
h=win32com.client.DispatchEx('HWPFrame.HwpObject');h.XHwpWindows.Item(0).Visible=False
try:
 print('insert',h.InsertPicture(str(root/'source_page_01.png'),True,0,False,False,0,0,0),flush=True)
 print('save',h.SaveAs(str(root/'native/picture.hwpx'),'HWPX',''),flush=True)
finally:h.Quit()
