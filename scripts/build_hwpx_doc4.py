"""[doc2] 시험지 N쪽(국어·영어)을 '문단 기반' 한글 문서로 재구성한다.
- 2단 편성(colPr), 문단 모양/글자 모양/스타일, 실제 표(지문·보기 상자), 문단 테두리, 글자 테두리,
  머리 표, 꼬리말(쪽 번호 자동) 사용. 배경 이미지·줄 단위 글상자 없음.
- 줄바꿈과 쪽/단 넘김은 한글 조판에 맡긴다.
usage: python scripts/build_hwpx_p1.py [--out PATH] [--ratio 95] [--spacing -2] [--probe]
"""
import argparse, re, zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=str(ROOT / 'output/native_p3/국어_1-3페이지.hwpx'))
ap.add_argument('--ratio', type=int, default=91)
ap.add_argument('--spacing', type=int, default=-3)
ap.add_argument('--pratio', type=int, default=None)
ap.add_argument('--pspacing', type=int, default=None)
ap.add_argument('--footer', type=float, default=0)
ap.add_argument('--nonlatin', default='BREAK_WORD')
ap.add_argument('--subject', default='국어')
ap.add_argument('--period', default='제1 교시')
ap.add_argument('--total', default='20')
ap.add_argument('--credit', default='Oni exam')
ap.add_argument('--preset', default='')
ap.add_argument('--prevk', type=float, default=1.0)
ap.add_argument('--adj', default='')
ap.add_argument('--area', default='사회탐구')
ap.add_argument('--eqfont', default='HYhwpEQ')
ap.add_argument('--advk', type=float, default=0.995)
ap.add_argument('--biggap', type=float, default=1.0)
ap.add_argument('--sub', default='')
ap.add_argument('--footer-nums', default='')
ap.add_argument('--lang', default='ko')
ap.add_argument('--tratio', type=int, default=99)
ap.add_argument('--items', default=str(ROOT / 'work/items_p1_3.json'))
ap.add_argument('--box-l', type=float, default=8.1, dest='box_l')
ap.add_argument('--box-r', type=float, default=4.4, dest='box_r')
ap.add_argument('--box-pad', type=float, default=4.0, dest='box_pad')
ap.add_argument('--box-off', type=float, default=0.0, dest='box_off')
ap.add_argument('--top2', type=float, default=156)
ap.add_argument('--hdr2', type=float, default=108)
args = ap.parse_args()
if args.pratio is None: args.pratio = 92
if args.pspacing is None: args.pspacing = -3

NS = ('xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
      'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
      'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
      'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"')
PT = 100
def u(pt): return round(pt * PT)

# ------------------------------------------------------------------ fonts
FONTS = ['HY신명조', 'HY견명조', 'HY중고딕', 'HY견고딕', 'Times New Roman', 'HY헤드라인M']
F_SIN, F_GYEON, F_JUNG, F_GYEONGO, F_TIMES, F_HEAD = range(6)
LANGS = ['HANGUL', 'LATIN', 'HANJA', 'JAPANESE', 'OTHER', 'SYMBOL', 'USER']
def fontfaces():
    fam = {0: 'FCAT_MYUNGJO', 1: 'FCAT_MYUNGJO', 2: 'FCAT_GOTHIC', 3: 'FCAT_GOTHIC', 4: 'FCAT_MYUNGJO', 5: 'FCAT_GOTHIC'}
    out = [f'<hh:fontfaces itemCnt="{len(LANGS)}">']
    for lg in LANGS:
        out.append(f'<hh:fontface lang="{lg}" fontCnt="{len(FONTS)}">')
        for i, f in enumerate(FONTS):
            out.append(f'<hh:font id="{i}" face="{f}" type="TTF" isEmbedded="0"><hh:typeInfo familyType="{fam[i]}" '
                       'weight="6" proportion="4" contrast="0" strokeVariation="1" armStyle="1" letterform="1" '
                       'midline="1" xHeight="1" /></hh:font>')
        out.append('</hh:fontface>')
    out.append('</hh:fontfaces>')
    return ''.join(out)

# ------------------------------------------------------------------ border fills
def bf(i, l=None, r=None, t=None, b=None):
    def side(tag, w):
        return (f'<hh:{tag} type="SOLID" width="{w}" color="#000000" />' if w
                else f'<hh:{tag} type="NONE" width="0.1 mm" color="#000000" />')
    return (f'<hh:borderFill id="{i}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0" /><hh:backSlash type="NONE" Crooked="0" isCounter="0" />'
            + side('leftBorder', l) + side('rightBorder', r) + side('topBorder', t) + side('bottomBorder', b)
            + '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000" /></hh:borderFill>')
BF_NONE, BF_NONE2, BF_BOX_THIN, BF_BOX_MID, BF_RULE = 1, 2, 3, 4, 5
def borderfills():
    items = [bf(1), bf(2),
             bf(3, *(['0.12 mm'] * 4)),          # 글자 테두리 / 지문·보기 상자
             bf(4, *(['0.2 mm'] * 4)),           # 문단 테두리(제1 교시, 홀수형, 쪽 번호)
             bf(5, None, None, None, '0.4 mm'),
             bf(6, None, None, '0.4 mm', '0.12 mm'), bf(7, None, None, None, '0.4 mm')]  # 머리 표 아래 굵은 선
    return f'<hh:borderFills itemCnt="{len(items)}">' + ''.join(items) + '</hh:borderFills>'

# ------------------------------------------------------------------ char shapes
CHARS = []
def char(font=F_SIN, size=11.2, ratio=None, spacing=None, bold=False, color='#000000', ul=False, box=False, ital=False):
    ratio = args.ratio if ratio is None else ratio
    spacing = args.spacing if spacing is None else spacing
    key = (font, size, ratio, spacing, bold, color, ul, box, ital)
    if key not in CHARS: CHARS.append(key)
    return CHARS.index(key)
def charprops():
    out = []
    for i, (font, size, ratio, spacing, bold, color, ul, box, ital) in enumerate(CHARS):
        a = lambda v: ' '.join(f'{k}="{v}"' for k in ['hangul', 'latin', 'hanja', 'japanese', 'other', 'symbol', 'user'])
        out.append(
            f'<hh:charPr id="{i}" height="{u(size)}" textColor="{color}" shadeColor="none" useFontSpace="{1 if font == F_TIMES else 0}" '
            f'useKerning="0" symMark="NONE" borderFillIDRef="{BF_BOX_THIN if box else BF_NONE2}">'
            f'<hh:fontRef hangul="{font}" latin="{font}" hanja="{font}" japanese="{font}" other="{font}" symbol="{font}" user="{font}" /><hh:ratio {a(ratio)} /><hh:spacing {a(spacing)} />'
            f'<hh:relSz {a(100)} /><hh:offset {a(0)} />'
            + ('<hh:italic />' if ital else '') + ('<hh:bold />' if bold else '')
            + f'<hh:underline type="{"BOTTOM" if ul else "NONE"}" shape="SOLID" color="#000000" />'
            '<hh:strikeout shape="NONE" color="#000000" /><hh:outline type="NONE" />'
            '<hh:shadow type="NONE" color="#C0C0C0" offsetX="10" offsetY="10" /></hh:charPr>')
    return f'<hh:charProperties itemCnt="{len(out)}">' + ''.join(out) + '</hh:charProperties>'

# ------------------------------------------------------------------ paragraph shapes
PARAS = []
def para(align='JUSTIFY', left=0, indent=0, right=0, line=18.4, prev=0, nxt=0, border=None, keep_next=False, pct=False, connect=False, tabs=None, atleast=False):
    key = (align, left, indent, right, line, prev, nxt, border, keep_next, pct, connect, tabs, atleast)
    if key not in PARAS: PARAS.append(key)
    return PARAS.index(key)
def paraprops():
    out = []
    for i, (align, left, indent, right, line, prev, nxt, border, keep_next, pct, connect, tabs, atleast) in enumerate(PARAS):
        out.append(
            f'<hh:paraPr id="{i}" tabPrIDRef="{tabpr(tabs) if tabs else 0}" condense="0" fontLineHeight="0" snapToGrid="0" '
            'suppressLineNumbers="0" checked="0" textDir="LTR">'
            f'<hh:align horizontal="{align}" vertical="BASELINE" /><hh:heading type="NONE" idRef="0" level="0" />'
            f'<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="{args.nonlatin}" widowOrphan="0" '
            f'keepWithNext="{1 if keep_next else 0}" keepLines="0" pageBreakBefore="0" lineWrap="BREAK" />'
            '<hh:autoSpacing eAsianEng="0" eAsianNum="0" />'
            f'<hh:margin><hc:intent value="{u(indent)}" unit="HWPUNIT" /><hc:left value="{u(left)}" unit="HWPUNIT" />'
            f'<hc:right value="{u(right)}" unit="HWPUNIT" /><hc:prev value="{u(prev)}" unit="HWPUNIT" />'
            f'<hc:next value="{u(nxt)}" unit="HWPUNIT" /></hh:margin>' +
            (f'<hh:lineSpacing type="PERCENT" value="100" unit="HWPUNIT" />' if pct else (f'<hh:lineSpacing type="AT_LEAST" value="{u(line)}" unit="HWPUNIT" />' if atleast else f'<hh:lineSpacing type="FIXED" value="{u(line)}" unit="HWPUNIT" />')) +
            f'<hh:border borderFillIDRef="{border or BF_NONE2}" offsetLeft="{u(args.box_off) if border else 0}" offsetRight="{u(args.box_off) if border else 0}" offsetTop="{u(args.box_off) if border else 0}" offsetBottom="{u(args.box_off) if border else 0}" connect="{1 if connect else 0}" ignoreMargin="0" /></hh:paraPr>')
    return f'<hh:paraProperties itemCnt="{len(out)}">' + ''.join(out) + '</hh:paraProperties>'

TABS = []
def tabpr(positions):
    key = tuple(positions)
    if key not in TABS: TABS.append(key)
    return 3 + TABS.index(key)
def tabprops_xml(seed_xml):
    items = ''.join(f'<hh:tabPr id="{3 + i}" autoTabLeft="0" autoTabRight="0">' + ''.join(
        f'<hh:tabItem pos="{u(p)}" type="LEFT" leader="NONE" />' for p in pos) + '</hh:tabPr>' for i, pos in enumerate(TABS))
    return seed_xml.replace('</hh:tabProperties>', items + '</hh:tabProperties>').replace('itemCnt="3"', f'itemCnt="{3 + len(TABS)}"', 1)

# ------------------------------------------------------------------ styles (이름 있는 스타일)
STYLES = []
def style(name, eng, pp, cp):
    STYLES.append((name, eng, pp, cp)); return len(STYLES) - 1
def styles_xml():
    out = [f'<hh:style id="{i}" type="PARA" name="{n}" engName="{e}" paraPrIDRef="{pp}" charPrIDRef="{cp}" '
           f'nextStyleIDRef="{i}" langID="1042" lockForm="0" />' for i, (n, e, pp, cp) in enumerate(STYLES)]
    return f'<hh:styles itemCnt="{len(out)}">' + ''.join(out) + '</hh:styles>'

# 기본 + 문서 스타일
ST_NORMAL = style('바탕글', 'Normal', para('JUSTIFY', line=16), char())
ST_BODY = style('지문', 'Passage', para('JUSTIFY', indent=10, right=0, line=18.4), char(ratio=args.pratio, spacing=args.pspacing))
ST_INSTR = style('발문 안내', 'Instruction', para('LEFT', line=16, prev=8, nxt=8), char(F_JUNG, 11.2, 100, 0))
ST_STEM = style('문항', 'Question', para('LEFT', left=11, indent=-11, line=18.4, prev=14, nxt=6, keep_next=True),
                char(F_GYEON, 12.7, None, None))
ST_CHOICE = style('선택지', 'Choice', para('JUSTIFY', left=21.2, indent=-10, line=18.4), char())
ST_BOX = style('보기 본문', 'BoxBody', para('JUSTIFY', indent=10.8, line=18.4), char(ratio=args.pratio, spacing=args.pspacing))
ST_BULLET = style('보기 항목', 'BoxItem', para('JUSTIFY', left=13, indent=-13, line=18.4), char(ratio=args.pratio, spacing=args.pspacing))
ST_BOXTITLE = style('보기 제목', 'BoxTitle', para('CENTER', line=18.4), char())
ST_HOST = style('개체 문단', 'ObjectHost', para('LEFT', pct=True), char())
ST_HOST_F = style('꼬리말 개체 문단', 'FooterObjectHost', para('CENTER', pct=True, prev=14), char())
ST_HOST_C = style('개체 문단(가운데)', 'ObjectHostCenter', para('CENTER', pct=True), char())
ST_HOST_IND = style('개체 문단(들여쓰기)', 'ObjectHostIndent', para('LEFT', left=10.8, pct=True), char())

# ------------------------------------------------------------------ run / paragraph builders
_id = [100000]
def nid():
    _id[0] += 1; return _id[0]

def run(text, cp):
    body = '<hp:tab width="4000" leader="0" type="1"/>'.join(escape(x) for x in text.split('	'))
    return f'<hp:run charPrIDRef="{cp}"><hp:t>{body}</hp:t></hp:run>'

def P(spans, st, col_break=False, extra_first=''):
    """spans: str | list of (text, charPrIdx)"""
    name, eng, pp, cp = STYLES[st]
    if isinstance(spans, str): spans = [(spans, cp)]
    body = ''.join(run(t, c) for t, c in spans)
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" '
            f'columnBreak="{1 if col_break else 0}" merged="0">{extra_first}{body}</hp:p>')

def tbl_host(tbl, st):
    name, eng, pp, cp = STYLES[st]
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{cp}">{tbl}</hp:run></hp:p>')

def cell(inner, col, row, w, h, bfid, valign='TOP', margin=(0, 0, 0, 0)):
    l, r, t, b = [u(m) for m in margin]
    return (f'<hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="{bfid}">'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="{valign}" linkListIDRef="0" '
            f'linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{inner}</hp:subList>'
            f'<hp:cellAddr colAddr="{col}" rowAddr="{row}" /><hp:cellSpan colSpan="1" rowSpan="1" />'
            f'<hp:cellSz width="{u(w)}" height="{u(h)}" /><hp:cellMargin left="{l}" right="{r}" top="{t}" bottom="{b}" /></hp:tc>')

def table(rows, widths, heights, bfid, margin=(0, 0, 0, 0), outer=(0, 0, 0, 0)):
    """rows: list of list of (inner_xml, bfid_or_None, valign)"""
    W, H = sum(widths), sum(heights)
    l, r, t, b = [u(m) for m in margin]
    trs = []
    for ri, row in enumerate(rows):
        tcs = ''.join(cell(inner, ci, ri, widths[ci], heights[ri], cb or bfid, va, margin)
                      for ci, (inner, cb, va) in enumerate(row))
        trs.append(f'<hp:tr>{tcs}</hp:tr>')
    return (f'<hp:tbl id="{nid()}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" '
            f'lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="0" rowCnt="{len(rows)}" colCnt="{len(widths)}" '
            f'cellSpacing="0" borderFillIDRef="{bfid}" noAdjust="0">'
            f'<hp:sz width="{u(W)}" widthRelTo="ABSOLUTE" height="{u(H)}" heightRelTo="ABSOLUTE" protect="0" />'
            '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" '
            'vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0" />'
            f'<hp:outMargin left="{u(outer[0])}" right="{u(outer[1])}" top="{u(outer[2])}" bottom="{u(outer[3])}" />'
            f'<hp:inMargin left="{l}" right="{r}" top="{t}" bottom="{b}" />' + ''.join(trs) + '</hp:tbl>')

# ---- 머리 표 (시험명 / 쪽 / 제1 교시 / 국어 영역 / 홀수형)
hd_title = P('2026학년도 대학수학능력시험 문제지',
             style('시험명', 'ExamTitle', para('CENTER', line=24), char(F_SIN, 19.4, 100, 0)))
hd_page = P('1', style('쪽 큰 숫자', 'BigPage', para('RIGHT', line=36), char(F_GYEON, 31.3, 100, 0)))
box_para = para('CENTER', left=0, right=0, line=24, border=BF_BOX_MID)
def boxed(inner_p, w, h):
    return tbl_host(table([[(inner_p, None, 'CENTER')]], [w], [h], BF_BOX_MID), ST_HOST_C)
hd_period = boxed(P(args.period, style('교시', 'Period', para('CENTER', line=24), char(F_GYEON, 19.7, 100, 0))), 91, 31)
hd_area = P(f'{args.subject} 영역', style('영역명', 'Area', para('CENTER', line=44), char(F_GYEONGO, 36, 100, 0)))
hd_type = boxed(P('홀수형', style('홀수/짝수형', 'ExamType', para('CENTER', line=34), char(F_GYEONGO, 25.8, 100, 0))), 80.7, 44)
blank = P('', ST_NORMAL)
head_tbl = table(
    [[(blank, None, 'CENTER'), (hd_title, None, 'CENTER'), (hd_page, None, 'CENTER')],
     [(hd_period, BF_RULE, 'CENTER'), (hd_area, BF_RULE, 'CENTER'), (hd_type, BF_RULE, 'CENTER')]],
    [96, 480, 90.4], [39, 71.3], BF_NONE)

# ---- 구역 설정 / 머리말·꼬리말
sec_pr = (
    '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" '
    'tabStopUnit="HWPUNIT" outlineShapeIDRef="1" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0">'
    '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0" />'
    '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0" />'
    '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" '
    'hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0" />'
    '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0" />'
    f'<hp:pagePr landscape="WIDELY" width="{u(842)}" height="{u(1191)}" gutterType="LEFT_ONLY">'
    f'<hp:margin header="0" footer="{u(args.footer)}" gutter="0" left="{u(87.8)}" right="{u(84.2)}" top="{u(107.8)}" bottom="{u(123.7)}" />'
    '</hp:pagePr>'
    '<hp:footNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0" />'
    '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000" />'
    '<hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850" /><hp:numbering type="CONTINUOUS" newNum="1" />'
    '<hp:placement place="EACH_COLUMN" beneathText="0" /></hp:footNotePr>'
    '<hp:endNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0" />'
    '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000" />'
    '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850" /><hp:numbering type="CONTINUOUS" newNum="1" />'
    '<hp:placement place="END_OF_DOCUMENT" beneathText="0" /></hp:endNotePr>'
    '<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417" /></hp:pageBorderFill>'
    '<hp:pageBorderFill type="EVEN" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417" /></hp:pageBorderFill>'
    '<hp:pageBorderFill type="ODD" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417" /></hp:pageBorderFill></hp:secPr>')

num_cp = char(F_SIN, 11.7, 100, 0)
ft_page_st = style('꼬리말 쪽번호', 'FooterPage', para('CENTER', line=16), num_cp)
ft_copy_st = style('꼬리말 변환 표기', 'FooterCredit', para('CENTER', line=12, prev=3),
                   char(F_JUNG, 9, 90, 0, color='#666666'))
auto_page = ('<hp:run charPrIDRef="%d"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" '
             'userChar="" prefixChar="" suffixChar="" supscript="0" /></hp:autoNum></hp:ctrl><hp:t> / %s</hp:t></hp:run>' % (num_cp, args.total))
page_p = (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[ft_page_st][2]}" styleIDRef="{ft_page_st}" pageBreak="0" columnBreak="0" merged="0">{auto_page}</hp:p>')
page_box = tbl_host(table([[(page_p, None, 'CENTER')]], [50.5], [22], BF_BOX_THIN), ST_HOST_F)
footer_sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
              f'linkListNextIDRef="0" textWidth="{u(666.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">'
              + page_box + '@@CREDIT@@'
              + '</hp:subList>')
footer_ctrl = f'<hp:ctrl><hp:footer id="{nid()}" applyPageType="BOTH">{footer_sub}</hp:footer></hp:ctrl>'
col1 = '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0" /></hp:ctrl>'
col2 = (f'<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="2" sameSz="1" sameGap="{u(28.2)}">'
        '<hp:colLine type="SOLID" width="0.4 mm" color="#000000" /></hp:colPr></hp:ctrl>')

# ================================================================== 문항 JSON → 문서 (v2)
import json, statistics
blocks = json.loads(Path(args.items).read_text(encoding='utf-8'))
def _fbox(f):
    if f['type'] == 'figure': return (f['x0'], f['y0'], f['x0'] + f['w'], f['y0'] + f['h'])
    xs, ys = f['xs'], f['ys']; return (f['x0'], f['y0'], f['x0'] + xs[-1] - xs[0], f['y0'] + ys[-1] - ys[0])

def group_pairs(pend):
    parts = [[f] for f in pend]
    merged = True
    while merged:
        merged = False
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                a = [_fbox(f) for f in parts[i]]; b = [_fbox(f) for f in parts[j]]
                ax0, ay0, ax1, ay1 = min(x[0] for x in a), min(x[1] for x in a), max(x[2] for x in a), max(x[3] for x in a)
                bx0, by0, bx1, by1 = min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b)
                vov = min(ay1, by1) - max(ay0, by0); hgap = max(ax0, bx0) - min(ax1, bx1)
                if vov > 0.4 * min(ay1 - ay0, by1 - by0) and hgap < 45:
                    parts[i] = sorted(parts[i] + parts[j], key=lambda f: _fbox(f)[0]); parts.pop(j); merged = True; break
            if merged: break
    out = []
    for g in parts:
        if len(g) == 1: out.append(g[0]); continue
        bx = [_fbox(f) for f in g]
        out.append({'type': 'composite', 'parts': g, 'page': g[0]['page'], 'col': g[0]['col'], 'x0': min(x[0] for x in bx), 'y0': min(x[1] for x in bx),
                    'w': max(x[2] for x in bx) - min(x[0] for x in bx), 'h': max(x[3] for x in bx) - min(x[1] for x in bx),
                    'float': True, 'col_start': any(f.get('col_start') for f in g)})
    return out

def attach_floats(bl):
    out, pend = [], []
    for b in bl:
        if b['type'] in ('figure', 'gtable') and b.get('float'): pend.append(b); continue
        if pend:
            pend = group_pairs(pend)
            ok = b['type'] not in ('figure', 'table', 'tagbox', 'gtable', 'choicetable', 'composite_inline') and all(f['page'] == b['page'] and f['col'] == b['col'] for f in pend)
            if ok:
                b['floats'] = pend
                b['col_start'] = b.get('col_start') or any(f.get('col_start') for f in pend)
            else:
                for f in pend: f['float'] = False; out.append(f)
            pend = []
        out.append(b)
    for f in group_pairs(pend):
        if f['type'] == 'composite': f['float'] = True; f['type'] = 'composite_inline'
        else: f['float'] = False
        out.append(f)
    return out

def merge_choice_tables(bl):
    """머리 줄(탭으로 나뉜 낱말) + 뒤따르는 가로 선택지 줄들 = 선(테두리) 없는 표 모양 선택지 → 네이티브 표"""
    out, i = [], 0
    while i < len(bl):
        b = bl[i]
        if (b.get('tabs') and b['type'] in ('passage', 'stemcont', 'bogi', 'dispeq') and i + 1 < len(bl) and bl[i + 1]['type'] == 'choice_row'
                and b['text'][:1] not in '①②③④⑤'):
            rows, j = [], i + 1
            while j < len(bl) and bl[j]['type'] == 'choice_row' and bl[j]['page'] == b['page'] and bl[j]['col'] == b['col']:
                rows.append(bl[j]); j += 1
            if rows[0].get('tabs') and len(rows[0]['tabs']) >= len(b['tabs']):
                out.append({'type': 'choicetable', 'header': b, 'rows': rows, 'page': b['page'], 'col': b['col'], 'y0': b['y0'], 'x0': rows[0]['x0'],
                            'gap': b.get('gap'), 'col_start': b.get('col_start'), 'box': None, 'runs': [], 'text': '[선택지 표]'})
                i = j; continue
        out.append(b); i += 1
    return out

blocks = attach_floats(merge_choice_tables(blocks))
for _i, _b in enumerate(blocks):
    if _i and blocks[_i - 1].get('floats'): _b['after_float'] = True
FCLS = {'head': F_HEAD, 'sin': F_SIN, 'gyeon': F_GYEON, 'gyeongo': F_GYEONGO, 'jung': F_JUNG, 'times': F_TIMES, 'sgraphic': F_JUNG}

def run_char(r, kind, adv=None, tr=None):
    inbox = kind in ('passage', 'label', 'bogi', 'bogi_item', 'bogi_title', 'notice')
    ratio = args.pratio if inbox else args.ratio
    spacing = args.pspacing if inbox else args.spacing
    if r['f'] == 'times':
        ratio, spacing = (max(88, min(100, round(tr * 100 * 0.993))) if tr and tr < 1.0 else args.tratio), 0
    if adv and r['f'] != 'times' and r['s'] <= 13.5:
        ratio, spacing = max(70, min(105, int(adv / r['s'] * 100 * args.advk))), 0
    if r['f'] in ('gyeongo', 'jung') and r['s'] > 15: ratio, spacing = 100, 0
    size = r['s']
    if size <= 13.5 and (ratio + spacing) != 100:      # 장평 100으로 두고 같은 글자 폭이 되도록 글자 크기를 줄인다
        size = max(7.0, round(size * (ratio + spacing) / 100, 1)); ratio, spacing = 100, 0
    SCALE[id(r)] = size / r['s']
    return char(FCLS[r['f']], size, ratio, spacing, bold=r.get('b', False), ital=r.get('i', False), ul=r['ul'], box=r['box'])

SCALE = {}
def credit_xml():
    """꼬리말 변환 표기: Oni Class 아이콘 + 'Oni exam'"""
    ico = pic_xml({'png': 'work/oni_icon.png', 'w': 9.6, 'h': 5.5}, None)
    cp = char(F_JUNG, 9, 90, 0, color='#666666')
    pp = STYLES[ft_copy_st][2]
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{ft_copy_st}" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{cp}">{ico}</hp:run>' + run('  ' + args.credit, cp) + '</hp:p>')

ADJ = json.loads(Path(args.adj).read_text(encoding='utf-8')) if args.adj and Path(args.adj).exists() else {}
def block_scale(b, t):
    for r in b.get('runs', []):
        if 'eq' not in r and r['t'].strip() and r['s'] <= 13.5 and r['f'] != 'gyeon':
            run_char(r, t, b.get('adv'), b.get('tr')); return SCALE[id(r)]
    return 0.9

BOXES = {'passage': dict(left=args.box_l, right=args.box_r, border=BF_BOX_THIN),
         'notice': dict(left=args.box_l, right=args.box_r, border=BF_BOX_THIN),
         'bogi': dict(left=(0 if args.preset == 'soc' else 10.8) + args.box_l, right=args.box_r, border=BF_BOX_THIN),
         'qbox': dict(left=args.box_l, right=args.box_r, border=BF_BOX_THIN)}

# 종류별 기본 줄 간격: 여러 줄 블록의 pitch 중앙값, 없으면 18.4
_p = {}
for b in blocks:
    if b.get('pitch'): _p.setdefault(b['type'], []).append(b['pitch'])
PITCH = {t: round(statistics.median(v), 1) for t, v in _p.items()}
def pitch_of(b): return b.get('pitch') or PITCH.get(b['type']) or (17.2 if args.lang == 'en' else 18.4)

_para_plain = para
def _para_eq(*a, **k):
    k['atleast'] = True
    return _para_plain(*a, **k)

QB_BASE = {}
for _b in blocks:
    if _b['type'] in ('qbox', 'bogi_item') and _b.get('x0') is not None:
        QB_BASE[_b['col']] = min(QB_BASE.get(_b['col'], 9999), _b.get('fx', _b['x0']))

def hang_para(b, prev_pt, box, ln, align='JUSTIFY'):
    base = QB_BASE.get(b['col'], b['x0']); fx = b.get('fx', b['x0']); cx = b.get('cx')
    kw = dict(prev=prev_pt, border=box['border'], right=box['right'], connect=True)
    if cx is not None and cx > fx + 3:   # 내어쓰기: 첫 줄이 left, 다음 줄은 left+hang (한글 방식)
        return para(align, left=box['left'] + (fx - base), indent=-(cx - fx), line=ln, **kw)
    if cx is not None and fx > cx + 3:   # 첫 줄 들여쓰기
        return para(align, left=box['left'] + (cx - base), indent=fx - cx, line=ln, **kw)
    return para(align, left=box['left'] + (fx - base), line=ln, **kw)

def block_para(b, prev_pt):
    return _block_para(b, prev_pt, any('eq' in r for r in b.get('runs', [])))

def _block_para(b, prev_pt, has_eq):
    para = _para_eq if has_eq else _para_plain
    t = b['type']; box = BOXES.get(b['box']) if b['box'] else None
    ln = pitch_of(b); kw = dict(prev=prev_pt)
    if t == 'qbox': return hang_para(b, prev_pt, box, ln)
    if t == 'dispeq': return para('LEFT', left=max(0, b['x0'] - (88 if b['col'] == 0 else 437)), line=ln, **kw)
    if t == 'stemcont': return para('LEFT', left=max(0, b['x0'] - (88 if b['col'] == 0 else 437)), line=ln, **kw)
    if t == 'instr': return para('LEFT', line=16, **kw)
    if t == 'stem': return para('LEFT', left=0, indent=-11, line=ln, keep_next=True, **kw)
    if t == 'choice': return para('LEFT', left=11.2, indent=-10, line=ln, **kw)
    if t == 'choice_row':
        tabs = tuple(round(11.2 + x, 1) for x in b['tabs'])
        return para('LEFT', left=11.2, line=ln, tabs=tabs, **kw)
    if t == 'footnote': return para('RIGHT', line=ln, **kw)
    if t == 'dialogue': return para('LEFT', left=11.2, line=ln, **kw)
    if t == 'notice': return para('JUSTIFY', indent=10, line=ln, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'label': return para('LEFT', line=ln, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'passage':
        if box: return para('JUSTIFY', indent=10, line=ln, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
        return para('JUSTIFY', left=11, indent=11, line=ln, **kw)
    if t == 'bogi_title': return para('CENTER', line=ln, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'bogi': return para('JUSTIFY', indent=10.8, line=ln, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'bogi_item': return hang_para(b, prev_pt, box, ln) if args.preset == 'soc' else para('JUSTIFY', left=box['left'], indent=-13, line=ln, border=box['border'], right=box['right'], connect=True, **kw)
    raise ValueError(t)

STYLE_OF = {}
def style_for(t):
    names = {'dispeq': ('별행 수식', 'DisplayEquation'), 'stemcont': ('문항 이어짐', 'QuestionCont'), 'tagbox': ('태그 상자', 'TagBoxText'), 'qbox': ('상자 지문', 'QuestionBox'), 'instr': ('발문 안내', 'Instruction'), 'stem': ('문항', 'Question'), 'choice': ('선택지', 'Choice'),
             'choice_row': ('선택지(가로)', 'ChoiceRow'), 'footnote': ('각주', 'Footnote'), 'dialogue': ('대화 빈칸', 'DialogueBlank'),
             'notice': ('안내 상자', 'NoticeBox'), 'label': ('지문 구분', 'PassageLabel'), 'passage': ('지문', 'Passage'),
             'bogi_title': ('보기 제목', 'BoxTitle'), 'bogi': ('보기 본문', 'BoxBody'), 'bogi_item': ('보기 항목', 'BoxItem'),
             'figure': ('그림', 'Figure'), 'table': ('표', 'Table')}
    if t not in STYLE_OF:
        n, e = names[t]; STYLE_OF[t] = style(n, e, para('JUSTIFY', line=18.4), char())
    return STYLE_OF[t]

IMAGES = []   # (id, path)
def pic_xml(b, fl=None):
    n = len(IMAGES) + 1; IMAGES.append((f'image{n}', b['png']))
    W, H = u(b['w']), u(b['h'])
    return (f'<hp:pic id="{nid()}" zOrder="0" numberingType="PICTURE" textWrap="{"SQUARE" if fl else "TOP_AND_BOTTOM"}" textFlow="BOTH_SIDES" lock="0" '
            f'dropcapstyle="None" href="" groupLevel="0" instid="{nid()}" reverse="0"><hp:offset x="0" y="0"/>'
            f'<hp:orgSz width="{W}" height="{H}"/><hp:curSz width="{W}" height="{H}"/><hp:flip horizontal="0" vertical="0"/>'
            '<hp:rotationInfo angle="0" centerX="0" centerY="0" rotateimage="1"/><hp:renderingInfo>'
            '<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
            '<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo>'
            f'<hc:img binaryItemIDRef="image{n}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
            f'<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="{W}" y="0"/><hc:pt2 x="{W}" y="{H}"/><hc:pt3 x="0" y="{H}"/></hp:imgRect>'
            '<hp:imgClip left="0" right="0" top="0" bottom="0"/><hp:inMargin left="0" right="0" top="0" bottom="0"/>'
            '<hp:imgDim dimwidth="0" dimheight="0"/><hp:effects/>'
            f'<hp:sz width="{W}" widthRelTo="ABSOLUTE" height="{H}" heightRelTo="ABSOLUTE" protect="0"/>'
            + (f'<hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
               f'horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="{u(fl[1])}" horzOffset="{u(fl[0])}"/>'
               '<hp:outMargin left="141" right="141" top="141" bottom="141"/>' if fl else
               '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
               'horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/>')
            + '<hp:shapeComment>시험지 그림</hp:shapeComment></hp:pic>')

def table_xml(b, prev_pt):
    """영어 표: 머리 행 + 데이터 행. 위·아래 굵은 선, 머리 아래 가는 선."""
    bnd = b['bounds']; widths = [bnd[i + 1] - bnd[i] for i in range(len(bnd) - 1)]
    cp = char(F_TIMES, 12.2, 100, 0); cpb = char(F_TIMES, 12.2, 100, 0, bold=True)
    pp = para('CENTER', line=15)
    st = style_for('table')
    def cellp(t, c): return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">'
                             + (run(t, c) if t else '') + '</hp:p>')
    def cell_runs(t):
        # 원 숫자와 ☓/○ 기호는 신명조, 나머지는 Times
        out = ''
        for seg in re.split(r'([①-⑤☓○])', t):
            if not seg: continue
            out += run(seg, cp if not re.match(r'[①-⑤☓○]', seg) else char(F_SIN, 11.2, 100, 0))
        return out
    def cellp2(t): return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">' + cell_runs(t) + '</hp:p>')
    hdr = [(cellp(h, cpb) if h else cellp('', cp), 6, 'CENTER') for h in b['header']]
    rows = [hdr]
    for ri, r in enumerate(b['rows']):
        last = ri == len(b['rows']) - 1
        rows.append([(cellp2(t), 7 if last else None, 'CENTER') for t in r])
    heights = [31] + [17.4] * len(b['rows'])
    tb = table(rows, widths, heights, BF_NONE, margin=(1, 1, 1, 1))
    cap = ''
    if b.get('caption'):
        cap_style = style('표 제목', 'TableCaption', para('CENTER', line=15, prev=prev_pt, nxt=3), cpb)
        capp = STYLES[cap_style]
        cap = (f'<hp:p id="{nid()}" paraPrIDRef="{capp[2]}" styleIDRef="{cap_style}" pageBreak="0" columnBreak="0" merged="0">'
               + run(b['caption'], cpb) + '</hp:p>')
    return cap, tb

NAT_KO = 6.6
def split_segments(runs):
    segs, cur = [], []
    for r in runs:
        if 'eq' not in r and '	' in r['t']:
            parts = r['t'].split('	')
            for k, part in enumerate(parts):
                if k: segs.append(cur); cur = []
                if part: cur.append(dict(r, t=part))
        else: cur.append(r)
    segs.append(cur)
    return [sg for sg in segs]

def choicetable_xml(b, prev_pt):
    h = b['header']; r0 = b['rows'][0]
    starts = [r0['x0']] + [r0['x0'] + t for t in r0['tabs']]
    widths = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)] + [72.0]
    hs = [h['x0']] + [h['x0'] + t for t in h['tabs']]
    hseg = split_segments(h.get('runs_tab', h['runs']))
    hcells = [[] for _ in starts]
    for st_, sg in zip(hs, hseg):
        k = min(range(len(starts)), key=lambda i: abs(starts[i] - st_)); hcells[k] = sg
    st = style('선택지 표 칸', 'ChoiceTableCell', para('LEFT', line=14, atleast=True), char())
    st_c = style('선택지 표 머리', 'ChoiceTableHead', para('CENTER', line=14, atleast=True), char())
    def cell_p(runs, head=False):
        pp = STYLES[st_c if head else st][2]; stx = st_c if head else st
        body = ''
        for r in runs:
            if 'eq' in r: body += eq_run(r['eq'], STYLES[st][3], 0.9)
            elif r['t']: body += run(r['t'], run_char(r, 'choice', None, None))
        return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{stx}" pageBreak="0" columnBreak="0" merged="0">{body}</hp:p>')
    rows = [[(cell_p(c, True), None, 'CENTER') for c in hcells]]
    heights = [max(16.0, r0['y0'] - h['y0'])]
    for k, r in enumerate(b['rows']):
        segs = split_segments(r['runs'])
        segs += [[] for _ in range(len(starts) - len(segs))]
        rows.append([(cell_p(c), None, 'CENTER') for c in segs[:len(starts)]])
        heights.append((b['rows'][k + 1]['y0'] - r['y0']) if k + 1 < len(b['rows']) else 26.0)
    return table(rows, widths, heights, BF_NONE, margin=(0, 0, 0, 0))

def gtable_xml(b, prev_pt, fl=None):
    xs, ys = b['xs'], b['ys']
    widths = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]; heights = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    st = style('표 칸', 'TableCell', para('CENTER', line=14, atleast=True), char())
    pp = STYLES[st][2]
    def cell_p(runs):
        body = ''
        for r in runs:
            if 'eq' in r: body += eq_run(r['eq'], STYLES[st][3], 0.9)
            elif r['t']: body += run(r['t'], run_char(r, 'table', None, None))
        return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">{body}</hp:p>')
    rows = [[(cell_p(c), None, 'CENTER') for c in row] for row in b['cells']]
    tb = table(rows, widths, heights, BF_BOX_THIN, margin=(1, 1, 0.5, 0.5))
    if fl:
        tb = re.sub(r'<hp:pos treatAsChar="1"[^>]*/>', f'<hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="{u(fl[1])}" horzOffset="{u(fl[0])}"/>', tb, count=1)
        tb = tb.replace('textWrap="TOP_AND_BOTTOM"', 'textWrap="SQUARE"', 1)
    return tb

def composite_xml(b, fl=None):
    parts = b['parts']; bx = [_fbox(f) for f in parts]
    x0 = b['x0']; widths, cells, xcur = [], [], x0
    for f, bb in zip(parts, bx):
        if bb[0] - xcur > 0.5: widths.append(bb[0] - xcur); cells.append(('', BF_NONE))
        w = bb[2] - bb[0]; widths.append(w)
        dy = bb[1] - b['y0']
        pp_ = para('LEFT', pct=True, prev=dy)
        sth = style('복합 칸', 'CompositeCell', pp_, char())
        inner = pic_xml(f, None) if f['type'] == 'figure' else gtable_xml(f, 0, None)
        cells.append((f'<hp:p id="{nid()}" paraPrIDRef="{pp_}" styleIDRef="{sth}" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{STYLES[sth][3]}">{inner}</hp:run></hp:p>', BF_NONE))
        xcur = bb[2]
    blank_p = P('', ST_NORMAL)
    row = [((c if c else blank_p), bf_, 'TOP') for c, bf_ in cells]
    tb = table([row], widths, [b['h']], BF_NONE)
    if fl:
        tb = re.sub(r'<hp:pos treatAsChar="1"[^>]*/>', f'<hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="{u(fl[1])}" horzOffset="{u(fl[0])}"/>', tb, count=1)
        tb = tb.replace('textWrap="TOP_AND_BOTTOM"', 'textWrap="SQUARE"', 1)
    return tb

def eq_run(e, cp, k=1.0):
    S = round(e['size'] * k, 1); W, H = u((e['w'] + 1.0) * k), u(e['h'] * k)
    return (f'<hp:run charPrIDRef="{cp}"><hp:equation id="{nid()}" zOrder="0" numberingType="EQUATION" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" '
            f'lock="0" dropcapstyle="None" version="Equation Version 60" baseLine="{max(1, min(99, round(e["bl"] * 100)))}" textColor="#000000" '
            f'baseUnit="{u(S)}" lineMode="CHAR" font="{args.eqfont}"><hp:sz width="{W}" widthRelTo="ABSOLUTE" height="{H}" heightRelTo="ABSOLUTE" protect="0"/>'
            '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" '
            'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/><hp:outMargin left="56" right="56" top="0" bottom="0"/>'
            f'<hp:shapeComment>수식입니다.</hp:shapeComment><hp:script>{escape(e["script"])}</hp:script></hp:equation></hp:run>')

NAT_KO_PLACEHOLDER = 0
def block_xml(b, i, bl, sec_first):
    prev_b = bl[i - 1] if i else None
    t = b['type']; gap = b['gap'] or 0
    nat = (pitch_of(b) - b['h']) if (b.get('h') and t not in ('figure', 'table')) else NAT_KO
    first_in_box = b['box'] and (not prev_b or prev_b['box'] != b['box'])
    prev = 0 if (b['col_start'] or b['gap'] is None) else max(0, gap - nat - (args.box_pad if first_in_box else 0))
    if t in ('choice', 'bogi', 'passage', 'bogi_item', 'choice_row', 'footnote') and gap and gap < 14 and b['box'] == (prev_b or {}).get('box'): prev = 0
    if t == 'stem' and prev_b and prev_b['box'] and not b['col_start']: prev = max(0, gap - nat - args.box_pad)
    cb = b['col_start'] and not sec_first
    if ADJ.get(f"{b['page']}-{b['col']}-{round(b['y0'])}") is not None: prev = max(0.0, prev + ADJ[f"{b['page']}-{b['col']}-{round(b['y0'])}"])
    if not b.get('after_float') and prev > 12:
        prev = 12 + (prev - 12) * args.prevk      # 큰 여백(풀이 공간)만 같은 비율로 줄인다. 작은 간격은 원본 그대로
        if prev > 100: prev = 100 + (prev - 100) * args.biggap
    if False: prev = 0   # 큰 풀이 여백은 일부 줄여 단 넘침을 막는다
    prev = round(prev, 1)
    if t == 'figure':
        pp = para('LEFT', left=b['x0'], pct=True, prev=prev)
        st = style_for('figure'); cp0 = STYLES[st][3]
        return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">'
                f'<hp:run charPrIDRef="{cp0}">{pic_xml(b)}</hp:run></hp:p>')
    if t == 'choicetable':
        tb = choicetable_xml(b, prev)
        host = style('선택지 표 문단', 'ChoiceTableHost', para('LEFT', left=max(0, b['x0'] - (88 if b['col'] == 0 else 437)), pct=True, prev=prev), char())
        return (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[host][2]}" styleIDRef="{host}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">'
                f'<hp:run charPrIDRef="{STYLES[host][3]}">{tb}</hp:run></hp:p>')
    if t == 'composite_inline':
        host = style('복합 문단', 'CompositeHost', para('LEFT', left=b['x0'], pct=True, prev=prev), char())
        return (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[host][2]}" styleIDRef="{host}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">'
                f'<hp:run charPrIDRef="{STYLES[host][3]}">{composite_xml(b, None)}</hp:run></hp:p>')
    if t == 'gtable':
        tb = gtable_xml(b, prev)
        host = style('표 문단', 'TableHost', para('LEFT', left=b['x0'], pct=True, prev=prev), char())
        return (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[host][2]}" styleIDRef="{host}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">'
                f'<hp:run charPrIDRef="{STYLES[host][3]}">{tb}</hp:run></hp:p>')
    if t == 'table':
        cap, tb = table_xml(b, prev)
        host = tbl_host(tb, ST_HOST)
        if cb and cap: cap = cap.replace('columnBreak="0"', 'columnBreak="1"', 1)
        return cap + host
    if t == 'tagbox':
        tb = table([[(P(b['text'], style('태그 상자', 'TagBox', para('CENTER', line=18), char(F_JUNG, 12.7, 100, 0, bold=True))), None, 'CENTER')]], [b.get('w', 110)], [23], BF_BOX_THIN)
        host = style('태그 상자 문단', 'TagBoxHost', para('LEFT', pct=True, prev=prev), char())
        return (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[host][2]}" styleIDRef="{host}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">'
                f'<hp:run charPrIDRef="{STYLES[host][3]}">{tb}</hp:run></hp:p>')
    pp = block_para(b, prev); st = style_for(t)
    runs = b['runs']
    if t == 'footnote': runs = [dict(r, t=r['t'].replace('\t', '   ')) for r in runs]
    kscale = block_scale(b, t)
    cp_any = [r for r in runs if 'eq' not in r and r['t']]
    def one(r):
        if 'eq' in r: return eq_run(r['eq'], STYLES[st][3], kscale)
        return run(r['t'], run_char(r, t, b.get('adv'), b.get('tr'))) if r['t'] else ''
    def flt(f):
        off = (f["x0"], max(0.0, f["y0"] - b["y0"] + prev))
        if f['type'] == 'composite': return composite_xml(f, off)
        return pic_xml(f, off) if f['type'] == 'figure' else gtable_xml(f, 0, off)
    fl_xml = ''.join(f'<hp:run charPrIDRef="{STYLES[st][3]}">{flt(f)}</hp:run>' for f in b.get('floats', []))
    body = fl_xml + ''.join(one(r) for r in runs)
    if t == 'dialogue':
        n = max(4, round(b.get('line_len', 300) / (0.5 * 12.2)))
        body += run(' ' + '_' * n, char(F_TIMES, 12.2, 100, 0))
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">{body}</hp:p>')

# ---- 머리말(2쪽~)
ST_HOST_R = style('개체 문단(오른쪽)', 'ObjectHostRight', para('RIGHT', pct=True), char())
def boxed_r(inner_p, w, h, host): return tbl_host(table([[(inner_p, None, 'CENTER')]], [w], [h], BF_BOX_MID), host)
def hdr_cell_num(align):
    pp = para(align, line=36); cp = char(F_GYEON, 31.3, 100, 0)
    st = style('쪽 큰 숫자(머리말)', 'HeaderPageNum', pp, cp)
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{cp}"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" userChar="" '
            f'prefixChar="" suffixChar="" supscript="0" /></hp:autoNum></hp:ctrl><hp:t></hp:t></hp:run></hp:p>')
title_p = P(f'{args.subject} 영역', style('머리말 영역명', 'HeaderArea', para('CENTER', line=36), char(F_GYEONGO, 28, 100, 0)))
type_style = style('머리말 홀수형', 'HeaderType', para('CENTER', line=24), char(F_GYEONGO, 18.9, 80, -2))
def type_box(host): return boxed_r(P('홀수형', type_style), 52, 22, host)
def header_xml(parity):
    num_l = parity == 'EVEN'
    left = hdr_cell_num('LEFT') if num_l else type_box(ST_HOST)
    right = type_box(ST_HOST_R) if num_l else hdr_cell_num('RIGHT')
    tb = table([[(left, None, 'CENTER'), (title_p, None, 'CENTER'), (right, None, 'CENTER')]], [150, 370.4, 150], [37], BF_NONE)
    sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
           f'linkListNextIDRef="0" textWidth="{u(670.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">'
           + tbl_host(tb, ST_HOST) + '</hp:subList>')
    return f'<hp:ctrl><hp:header id="{nid()}" applyPageType="{parity}">{sub}</hp:header></hp:ctrl>'

def make_sec_pr(top_pt, start_page, header_pt):
    sp = re.sub(r'(<hp:margin header=)"\d+"( footer="\d+" gutter="0" left="\d+" right="\d+") top="\d+"', rf'\g<1>"{u(header_pt)}"\g<2> top="{u(top_pt)}"', sec_pr)
    return re.sub(r'(<hp:startNum pageStartsOn="BOTH" page=)"\d+"', rf'\g<1>"{start_page}"', sp)

pages_first = [b for b in blocks if b['page'] == blocks[0]['page']]
rest = [b for b in blocks if b['page'] != blocks[0]['page']]
name, eng, pp_host, cp_host = STYLES[ST_HOST]
ST_TINY = style('구역 정의', 'SectionDef', para('LEFT', line=1.0), char(F_SIN, 1.0, 100, 0))
def host_first(sec_pr_xml, extra_ctrls, content_before):
    tiny = not content_before
    sid = ST_TINY if tiny else ST_HOST
    return (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[sid][2]}" styleIDRef="{sid}" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{STYLES[sid][3]}">{sec_pr_xml}{col1}{extra_ctrls}{content_before}</hp:run></hp:p>')
def col2_run(cp): return f'<hp:run charPrIDRef="{cp}">{col2}</hp:run>'
def section_xml(sec_blocks, top_pt, start_page, header_pt, head_content, extra_ctrls, head_extra=''):
    out = []
    if head_content:   # 1쪽: 머리 표가 든 문단 + 1단 정의 뒤 2단 전환
        out.append(host_first(make_sec_pr(top_pt, start_page, header_pt), extra_ctrls, head_content) + head_extra)
    for i, b in enumerate(sec_blocks):
        x = block_xml(b, i, sec_blocks, sec_first=(i == 0))
        if i == 0:
            stt = style_for(b['type']) if b['type'] not in ('table',) else style_for('table')
            cp0 = STYLES[stt][3]
            lead = col2_run(cp0)
            if not head_content:   # 2쪽~: 구역·꼬리말·머리말·2단 정의를 첫 문단 안에 둔다(빈 줄을 만들지 않음)
                lead = f'<hp:run charPrIDRef="{cp0}">{make_sec_pr(top_pt, start_page, header_pt)}{col2}{extra_ctrls}</hp:run>'
            x = x.replace('merged="0">', 'merged="0">' + lead, 1)
        out.append(x)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><hs:sec {NS}>' + ''.join(out) + '</hs:sec>'

def footer_ctrl_text(label):
    pp_ = (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[ft_page_st][2]}" styleIDRef="{ft_page_st}" pageBreak="0" columnBreak="0" merged="0">'
           f'{run(label, num_cp)}</hp:p>')
    bx = tbl_host(table([[(pp_, None, 'CENTER')]], [50.5], [22], BF_BOX_THIN), ST_HOST_F)
    sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
           f'textWidth="{u(666.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">' + bx + '@@CREDIT@@' + '</hp:subList>')
    return f'<hp:ctrl><hp:footer id="{nid()}" applyPageType="BOTH">{sub}</hp:footer></hp:ctrl>'

def cell_par(runs, align, line=36):
    pp = para(align, line=line)
    st = style('머리 셀', 'HeaderCell', pp, runs[0][1])
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">'
            + ''.join(run(t, c) for t, c in runs) + '</hp:p>')

def header_custom(left, right, la, ra):
    tb = table([[(cell_par(left, la), None, 'CENTER'), (blank, None, 'CENTER'), (cell_par(right, ra), None, 'CENTER')]],
               [250, 170.4, 250], [37], BF_NONE)
    sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
           f'textWidth="{u(670.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">' + tbl_host(tb, ST_HOST) + '</hp:subList>')
    return f'<hp:ctrl><hp:header id="{nid()}" applyPageType="BOTH">{sub}</hp:header></hp:ctrl>'

def soc_head():
    big = char(F_GYEON, 31.3, 100, 0); ttl = char(F_GYEONGO, 37.9, 100, 0); sm = char(F_HEAD, 20, 100, 0)
    r1 = [(blank, None, 'CENTER'), (hd_title, None, 'CENTER'), (cell_par([('1', big)], 'RIGHT'), None, 'CENTER')]
    area = cell_par([((args.area + ' 영역'), ttl), ('(' + args.sub + ')', sm)], 'CENTER', 46)
    r2 = [(hd_period, None, 'CENTER'), (area, None, 'CENTER'), (blank, None, 'CENTER')]
    top = table([r1, r2], [96, 480, 90.4], [39, 57], BF_NONE)
    lab = char(F_JUNG, 14, 100, 0)
    def c(t=''): return cell_par([(t, lab)], 'CENTER', 20)
    cells = ([('성명', 39, 3), ('', 148, 3), ('', 16, 1), ('수험 번호', 71, 3)] + [('', 22, 3)] * 4 + [('-', 18, 3)]
             + [('', 20, 3)] * 4 + [('', 16, 1), ('제(  )선택', 88, 3)])
    gt = table([[(c(t), bf_, 'CENTER') for t, w, bf_ in cells]], [w for t, w, bf_ in cells], [24], BF_NONE)
    outer_pp = para('LEFT', left=47, pct=True)
    st_o = style('성명 칸 문단', 'NameFieldHost', outer_pp, char())
    grid_host = (f'<hp:p id="{nid()}" paraPrIDRef="{outer_pp}" styleIDRef="{st_o}" pageBreak="0" columnBreak="0" merged="0">'
                 f'<hp:run charPrIDRef="{STYLES[st_o][3]}">{gt}</hp:run></hp:p>')
    rule = table([[(grid_host, BF_RULE, 'CENTER')]], [666.4], [38], BF_NONE)
    return top, tbl_host(rule, ST_HOST)

SOC = args.preset == 'soc'
secs = []
if SOC:
    fn = [x for x in args.footer_nums.split(',') if x]
    pgs = sorted({b['page'] for b in blocks})
    for idx, pg in enumerate(pgs):
        bl = [b for b in blocks if b['page'] == pg]
        flabel = f"{fn[idx] if idx < len(fn) else pg} / {args.total}"
        fctrl = footer_ctrl_text(flabel)
        if idx == 0:
            top_tbl, rule_para = soc_head()
            secs.append(section_xml(bl, 107.8, 1, 0, top_tbl, fctrl, head_extra=rule_para))
        else:
            big = char(F_GYEON, 31.3, 100, 0); sm = char(F_HEAD, 20, 100, 0); ttl = char(F_GYEONGO, 28, 100, 0)
            sub_ = '(' + args.sub + ')'
            if pg % 2 == 0:
                hdr = header_custom([(str(pg), big), (' ' + sub_, sm)], [((args.area + ' 영역'), ttl)], 'LEFT', 'RIGHT')
            else:
                hdr = header_custom([((args.area + ' 영역'), ttl)], [(args.sub, char(F_HEAD, 20, 100, 0, box=True)), (' ' + str(pg), big)], 'LEFT', 'RIGHT')
            secs.append(section_xml(bl, args.top2, pg, args.hdr2, '', fctrl + hdr))
else:
    secs.append(section_xml(pages_first, 107.8, 1, 0, head_tbl, footer_ctrl))
    if rest:
        secs.append(section_xml(rest, args.top2, 2, args.hdr2, '',
                    footer_ctrl.replace(footer_ctrl.split('"')[1], str(nid()), 1) + header_xml('EVEN') + header_xml('ODD')))

secs = [re.sub('@@CREDIT@@', lambda m: credit_xml(), x) for x in secs]

# ================================================================== 패키지
with zipfile.ZipFile(ROOT / 'work/seed_package.hwpx') as z:
    seed = {n: z.read(n) for n in z.namelist()}
head = seed['Contents/header.xml'].decode('utf-8')
def swap(tag, new):
    global head
    head, n = re.subn(rf'<hh:{tag} itemCnt="\d+">.*?</hh:{tag}>', lambda m: new, head, flags=re.S)
    assert n == 1, tag
swap('fontfaces', fontfaces()); swap('borderFills', borderfills())
swap('charProperties', charprops()); swap('paraProperties', paraprops()); swap('styles', styles_xml())
m = re.search(r'<hh:tabProperties itemCnt="\d+">.*?</hh:tabProperties>', head, flags=re.S)
head = head.replace(m.group(0), tabprops_xml(m.group(0)))
head = head.replace('secCnt="1"', f'secCnt="{len(secs)}"')
hpf = seed['Contents/content.hpf'].decode('utf-8')
hpf = re.sub(r'<opf:item id="image1"[^>]*/>', '', hpf)
items = ''.join(f'<opf:item id="{iid}" href="BinData/{iid}.png" media-type="image/png" isEmbeded="1" />' for iid, _ in IMAGES)
items = ''.join(f'<opf:item id="section{k}" href="Contents/section{k}.xml" media-type="application/xml" />' for k in range(1, len(secs))) + items
hpf = hpf.replace('<opf:item id="settings"', items + '<opf:item id="settings"', 1)
hpf = hpf.replace('<opf:itemref idref="section0" linear="yes" />', '<opf:itemref idref="section0" linear="yes" />' + ''.join(f'<opf:itemref idref="section{k}" linear="yes" />' for k in range(1, len(secs))))
prv = '\n'.join(b['text'] for b in blocks)[:1000]
out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr(zipfile.ZipInfo('mimetype'), seed['mimetype'], compress_type=zipfile.ZIP_STORED)
    for n, data in seed.items():
        if n == 'mimetype' or n.startswith('BinData/'): continue
        if n == 'Contents/header.xml': data = head.encode('utf-8')
        elif n == 'Contents/content.hpf': data = hpf.encode('utf-8')
        elif n == 'Contents/section0.xml': data = secs[0].encode('utf-8')
        elif n == 'Preview/PrvText.txt': data = prv.encode('utf-8')
        z.writestr(n, data)
    for k in range(1, len(secs)): z.writestr(f'Contents/section{k}.xml', secs[k].encode('utf-8'))
    for iid, path in IMAGES: z.write(ROOT / path, f'BinData/{iid}.png')
print('wrote', out, 'blocks', len(blocks), 'styles', len(STYLES), 'charPr', len(CHARS), 'paraPr', len(PARAS), 'images', len(IMAGES))
