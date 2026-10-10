import sys
from pathlib import Path
import win32com.client

out = Path(sys.argv[1]).resolve()
tests = sys.argv[2:]
h = win32com.client.DispatchEx('HWPFrame.HwpObject')
h.XHwpWindows.Item(0).Visible = True
try:
    h.RegisterModule('FilePathCheckDLL', 'SecurityModule')
    for t in tests:
        x = h.HParameterSet.HInsertText
        x.Text = t + '   =>   '
        h.HAction.Execute('InsertText', x.HSet)
        e = h.HParameterSet.HEqEdit
        h.HAction.GetDefault('EquationCreate', e.HSet)
        e.string = t
        e.BaseUnit = 1100
        e.LineMode = 0
        h.HAction.Execute('EquationCreate', e.HSet)
        h.HAction.Run('BreakPara')
    h.SaveAs(str(out), 'PDF', '')
finally:
    h.Quit()
