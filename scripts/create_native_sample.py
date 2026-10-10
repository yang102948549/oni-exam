from pathlib import Path
import win32com.client
root=Path('output/korean_exam_test/native').resolve()
h=win32com.client.DispatchEx('HWPFrame.HwpObject')
h.XHwpWindows.Item(0).Visible=False
try:
 print('version',h.Version,flush=True)
 p=h.HParameterSet.HTableCreation
 h.HAction.GetDefault('TableCreate',p.HSet)
 p.Rows=1;p.Cols=1;p.WidthType=2;p.HeightType=1;p.WidthValue=30000;p.HeightValue=4000
 p.CreateItemArray('ColWidth',1);p.ColWidth.SetItem(0,30000)
 p.CreateItemArray('RowHeight',1);p.RowHeight.SetItem(0,4000)
 print('table',h.HAction.Execute('TableCreate',p.HSet),flush=True)
 t=h.HParameterSet.HInsertText;t.Text='변환 시험 문단입니다.';h.HAction.Execute('InsertText',t.HSet)
 print('save',h.SaveAs(str(root/'sample.hwpx'),'HWPX',''),flush=True)
finally:h.Quit()
