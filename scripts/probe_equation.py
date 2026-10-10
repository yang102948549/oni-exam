"""한글 COM으로 수식 개체를 하나 만들어 HWPX XML 형태를 확인한다(연구용)."""
import sys, zipfile
from pathlib import Path
import win32com.client

out = Path(sys.argv[1]).resolve()
h = win32com.client.DispatchEx('HWPFrame.HwpObject')
h.XHwpWindows.Item(0).Visible = True
try:
    print('SEC', h.RegisterModule('FilePathCheckDLL', 'SecurityModule'), flush=True)
    t = h.HParameterSet.HInsertText
    t.Text = '다음 식의 값은 '
    h.HAction.Execute('InsertText', t.HSet)
    e = h.HParameterSet.HEqEdit
    h.HAction.GetDefault('EquationCreate', e.HSet)
    e.string = r'{x^2 + 3x - 1} over {sqrt {2}} + int _0 ^1 f(x)dx'
    e.BaseUnit = 1000
    e.LineMode = 0
    print('EQ', h.HAction.Execute('EquationCreate', e.HSet), flush=True)
    print('SAVE', h.SaveAs(str(out), 'HWPX', ''), flush=True)
finally:
    h.Quit()
z = zipfile.ZipFile(out)
s = z.read('Contents/section0.xml').decode('utf-8')
i = s.find('<hp:equation')
print(s[i - 200:i + 1800] if i >= 0 else 'NO EQUATION FOUND')
