"""Page 1 of 국어.pdf rebuilt as a *native* Hancom document (paragraph flow, 2 columns,
styles, real tables) by driving Hancom COM. No background image, no per-line frames.
Usage: python scripts/build_native_p1.py [--out PATH] [--ratio 95] [--spacing -2]
"""
import argparse, json
from pathlib import Path
import win32com.client

ap = argparse.ArgumentParser()
ap.add_argument('--out', default='output/native_p1/국어_1페이지_네이티브.hwpx')
ap.add_argument('--ratio', type=int, default=95)    # 장평
ap.add_argument('--spacing', type=int, default=-2)  # 자간 %
ap.add_argument('--pdf', default='')
args = ap.parse_args()
out = Path(args.out).resolve(); out.parent.mkdir(parents=True, exist_ok=True)

SINMYEONG, GYEONMYEONG, JUNGGO, GYEONGO = 'HY신명조', 'HY견명조', 'HY중고딕', 'HY견고딕'
PT = 100  # HWPUNIT per pt

h = win32com.client.DispatchEx('HWPFrame.HwpObject')
h.XHwpWindows.Item(0).Visible = False
try:
    h.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
except Exception:
    pass

def act(name, setter=None):
    ps = None
    if setter:
        ps = setter()
        return h.HAction.Execute(name, ps.HSet)
    return h.HAction.Run(name)

def page_setup():
    s = h.HParameterSet.HSecDef
    h.HAction.GetDefault('PageSetup', s.HSet)
    pd = s.PageDef
    pd.PaperWidth = round(842 * PT); pd.PaperHeight = round(1191 * PT)
    pd.Landscape = 0
    pd.LeftMargin = round(87.8 * PT); pd.RightMargin = round(87.8 * PT)
    pd.TopMargin = round(107.8 * PT); pd.BottomMargin = round(100 * PT)
    pd.HeaderLen = 0; pd.FooterLen = round(30 * PT); pd.GutterLen = 0
    pd.PaperWidth = round(842 * PT)
    s.HSet.SetItem('ApplyClass', 24); s.HSet.SetItem('ApplyTo', 3)
    return h.HAction.Execute('PageSetup', s.HSet)

def char(font=None, size=None, bold=None, ratio=None, spacing=None, color=None):
    a = h.HParameterSet.HCharShape
    h.HAction.GetDefault('CharShape', a.HSet)
    if font:
        for f in ('FaceNameHangul', 'FaceNameLatin', 'FaceNameHanja', 'FaceNameJapanese',
                  'FaceNameOther', 'FaceNameSymbol', 'FaceNameUser'):
            setattr(a, f, font)
    if size is not None: a.Height = round(size * PT)
    if bold is not None: a.Bold = 1 if bold else 0
    if ratio is not None:
        for f in ('Hangul', 'Latin', 'Hanja', 'Japanese', 'Other', 'Symbol', 'User'):
            setattr(a, 'Ratio' + f, ratio)
    if spacing is not None:
        for f in ('Hangul', 'Latin', 'Hanja', 'Japanese', 'Other', 'Symbol', 'User'):
            setattr(a, 'Spacing' + f, spacing)
    if color is not None: a.TextColor = color
    return h.HAction.Execute('CharShape', a.HSet)

def para(align='Justify', left=0, indent=0, line=18.4, before=0, after=0):
    a = h.HParameterSet.HParaShape
    h.HAction.GetDefault('ParagraphShape', a.HSet)
    a.AlignType = {'Justify': 0, 'Left': 1, 'Right': 2, 'Center': 3}[align]
    a.LeftMargin = round(left * PT); a.Indentation = round(indent * PT); a.RightMargin = 0
    a.LineSpacingType = 1; a.LineSpacing = round(line * PT)   # 고정 줄 간격
    a.PrevSpacing = round(before * PT); a.NextSpacing = round(after * PT)
    a.SnapToGrid = 0
    return h.HAction.Execute('ParagraphShape', a.HSet)

def text(t):
    a = h.HParameterSet.HInsertText; a.Text = t
    return h.HAction.Execute('InsertText', a.HSet)

def enter(): h.HAction.Run('BreakPara')

def body(font=SINMYEONG, size=11.2, bold=False):
    char(font, size, bold, args.ratio, args.spacing)

def table(rows, cols, widths_pt, heights_pt=None):
    t = h.HParameterSet.HTableCreation
    h.HAction.GetDefault('TableCreate', t.HSet)
    t.Rows = rows; t.Cols = cols; t.WidthType = 2; t.HeightType = 1
    t.WidthValue = round(sum(widths_pt) * PT)
    t.HeightValue = round((heights_pt[0] if heights_pt else 20) * PT)
    t.CreateItemArray('ColWidth', cols)
    for i, w in enumerate(widths_pt): t.ColWidth.SetItem(i, round(w * PT))
    t.CreateItemArray('RowHeight', rows)
    for i in range(rows):
        t.RowHeight.SetItem(i, round((heights_pt[i] if heights_pt else 20) * PT))
    t.TableProperties.TreatAsChar = 1
    return h.HAction.Execute('TableCreate', t.HSet)

def cell_border(sides, width='0.12 mm'):
    """sides: subset of 'LRTB' drawn; others none. Applies to selected cells."""
    a = h.HParameterSet.HCellBorderFill
    h.HAction.GetDefault('CellBorder', a.HSet)
    for s in 'LRTB':
        nm = {'L': 'Left', 'R': 'Right', 'T': 'Top', 'B': 'Bottom'}[s]
        on = s in sides
        setattr(a, 'BorderType' + nm, 1 if on else 0)
        setattr(a, 'BorderWidth' + nm, 1 if on else 0)
    return h.HAction.Execute('CellBorder', a.HSet)

def cell_margin_valign(l=0, r=0, t=0, b=0, valign=1):
    a = h.HParameterSet.HShapeObject
    h.HAction.GetDefault('TablePropertyDialog', a.HSet)

def exit_table(): h.HAction.Run('MoveDocEnd') if False else h.HAction.Run('TableRightCell')

try:
    print('version', h.Version, flush=True)
    print('page_setup', page_setup(), flush=True)

    # ---------- 머리 블록 (1단) ----------
    # 줄 1: 시험명 + 쪽 큰 숫자
    para('Center', line=24, after=0); char(SINMYEONG, 19.4, False, 100, 0)
    text('2026학년도 대학수학능력시험 문제지'); enter()
    # 줄 2: 3열 표 (제1 교시 | 국어 영역 | 홀수형)
    para('Left', line=14); char(SINMYEONG, 11, False, 100, 0)
    print('table', table(1, 3, [92, 483, 91.2], [52]), flush=True)
    # 셀 내용
    char(GYEONMYEONG, 19.7, True, 100, 0); para('Center', line=24)
    text('제1 교시')
    h.HAction.Run('TableRightCell')
    char(GYEONGO, 36, False, 100, 0); para('Center', line=44)
    text('국어 영역')
    h.HAction.Run('TableRightCell')
    char(GYEONGO, 25.8, False, 100, 0); para('Center', line=30)
    text('홀수형')
    h.HAction.Run('TableCellBlock')  # not essential
    # 표 밖으로 이동
    h.HAction.Run('MoveDocEnd')
    para('Left', line=2); char(SINMYEONG, 1, False, 100, 0)
    enter()
    # ---------- 2단 ----------
    c = h.HParameterSet.HColDef
    h.HAction.GetDefault('MultiColumn', c.HSet)
    c.Count = 2; c.SameGap = round(31 * PT); c.SameSize = 1; c.Type = 0
    c.LineType = 1; c.LineWidth = 6
    c.HSet.SetItem('ApplyClass', 832); c.HSet.SetItem('ApplyTo', 6)
    print('columns', h.HAction.Execute('MultiColumn', c.HSet), flush=True)

    # ---------- 왼쪽 단 ----------
    para('Left', line=16); char(JUNGGO, 11.2, False, 100, 0)
    text('[1～3] 다음 글을 읽고 물음에 답하시오.'); enter()
    # 지문 박스 (1셀 표)
    print('passage table', table(1, 1, [317.6], [595]), flush=True)
    passage = open(Path(__file__).with_name('p1_passage.txt'), encoding='utf-8').read().strip().split('\n')
    first = True
    for line in passage:
        para('Justify', left=0, indent=10, line=18.4)
        body()
        text(line)
        if line is not passage[-1]: enter()
    h.HAction.Run('CloseEx') if False else None
    h.HAction.Run('MoveDocEnd')
    # (이후 문항/선택지는 build 2단계에서 계속)
    print('save', h.SaveAs(str(out), 'HWPX', ''), flush=True)
    if args.pdf: print('pdf', h.SaveAs(str(Path(args.pdf).resolve()), 'PDF', ''), flush=True)
    print('pages', h.PageCount, flush=True)
finally:
    h.Quit()
