"""[doc] 국어 1~3쪽을 '문단 기반' 한글 문서로 재구성한다.
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
FONTS = ['HY신명조', 'HY견명조', 'HY중고딕', 'HY견고딕']
F_SIN, F_GYEON, F_JUNG, F_GYEONGO = range(4)
LANGS = ['HANGUL', 'LATIN', 'HANJA', 'JAPANESE', 'OTHER', 'SYMBOL', 'USER']
def fontfaces():
    fam = {0: 'FCAT_MYUNGJO', 1: 'FCAT_MYUNGJO', 2: 'FCAT_GOTHIC', 3: 'FCAT_GOTHIC'}
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
             bf(5, None, None, None, '0.4 mm')]  # 머리 표 아래 굵은 선
    return f'<hh:borderFills itemCnt="{len(items)}">' + ''.join(items) + '</hh:borderFills>'

# ------------------------------------------------------------------ char shapes
CHARS = []
def char(font=F_SIN, size=11.2, ratio=None, spacing=None, bold=False, color='#000000', ul=False, box=False):
    ratio = args.ratio if ratio is None else ratio
    spacing = args.spacing if spacing is None else spacing
    key = (font, size, ratio, spacing, bold, color, ul, box)
    if key not in CHARS: CHARS.append(key)
    return CHARS.index(key)
def charprops():
    out = []
    for i, (font, size, ratio, spacing, bold, color, ul, box) in enumerate(CHARS):
        a = lambda v: ' '.join(f'{k}="{v}"' for k in ['hangul', 'latin', 'hanja', 'japanese', 'other', 'symbol', 'user'])
        out.append(
            f'<hh:charPr id="{i}" height="{u(size)}" textColor="{color}" shadeColor="none" useFontSpace="0" '
            f'useKerning="0" symMark="NONE" borderFillIDRef="{BF_BOX_THIN if box else BF_NONE2}">'
            f'<hh:fontRef {a(font)} /><hh:ratio {a(ratio)} /><hh:spacing {a(spacing)} />'
            f'<hh:relSz {a(100)} /><hh:offset {a(0)} />'
            + ('<hh:bold />' if bold else '')
            + f'<hh:underline type="{"BOTTOM" if ul else "NONE"}" shape="SOLID" color="#000000" />'
            '<hh:strikeout shape="NONE" color="#000000" /><hh:outline type="NONE" />'
            '<hh:shadow type="NONE" color="#C0C0C0" offsetX="10" offsetY="10" /></hh:charPr>')
    return f'<hh:charProperties itemCnt="{len(out)}">' + ''.join(out) + '</hh:charProperties>'

# ------------------------------------------------------------------ paragraph shapes
PARAS = []
def para(align='JUSTIFY', left=0, indent=0, right=0, line=18.4, prev=0, nxt=0, border=None, keep_next=False, pct=False, connect=False):
    key = (align, left, indent, right, line, prev, nxt, border, keep_next, pct, connect)
    if key not in PARAS: PARAS.append(key)
    return PARAS.index(key)
def paraprops():
    out = []
    for i, (align, left, indent, right, line, prev, nxt, border, keep_next, pct, connect) in enumerate(PARAS):
        out.append(
            f'<hh:paraPr id="{i}" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="0" '
            'suppressLineNumbers="0" checked="0" textDir="LTR">'
            f'<hh:align horizontal="{align}" vertical="BASELINE" /><hh:heading type="NONE" idRef="0" level="0" />'
            f'<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="{args.nonlatin}" widowOrphan="0" '
            f'keepWithNext="{1 if keep_next else 0}" keepLines="0" pageBreakBefore="0" lineWrap="BREAK" />'
            '<hh:autoSpacing eAsianEng="0" eAsianNum="0" />'
            f'<hh:margin><hc:intent value="{u(indent)}" unit="HWPUNIT" /><hc:left value="{u(left)}" unit="HWPUNIT" />'
            f'<hc:right value="{u(right)}" unit="HWPUNIT" /><hc:prev value="{u(prev)}" unit="HWPUNIT" />'
            f'<hc:next value="{u(nxt)}" unit="HWPUNIT" /></hh:margin>' +
            (f'<hh:lineSpacing type="PERCENT" value="100" unit="HWPUNIT" />' if pct else f'<hh:lineSpacing type="FIXED" value="{u(line)}" unit="HWPUNIT" />') +
            f'<hh:border borderFillIDRef="{border or BF_NONE2}" offsetLeft="{u(args.box_off) if border else 0}" offsetRight="{u(args.box_off) if border else 0}" offsetTop="{u(args.box_off) if border else 0}" offsetBottom="{u(args.box_off) if border else 0}" connect="{1 if connect else 0}" ignoreMargin="0" /></hh:paraPr>')
    return f'<hh:paraProperties itemCnt="{len(out)}">' + ''.join(out) + '</hh:paraProperties>'

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
    return f'<hp:run charPrIDRef="{cp}"><hp:t>{escape(text)}</hp:t></hp:run>'

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
hd_period = boxed(P('제1 교시', style('교시', 'Period', para('CENTER', line=24), char(F_GYEON, 19.7, 100, 0))), 91, 31)
hd_area = P('국어 영역', style('영역명', 'Area', para('CENTER', line=44), char(F_GYEONGO, 36, 100, 0)))
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
ft_copy_st = style('꼬리말 저작권', 'FooterCopyright', para('LEFT', left=407.2, line=12, prev=3),
                   char(F_JUNG, 10, 90, 0, color='#0000FF'))
auto_page = ('<hp:run charPrIDRef="%d"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" '
             'userChar="" prefixChar="" suffixChar="" supscript="0" /></hp:autoNum></hp:ctrl><hp:t> / 20</hp:t></hp:run>' % num_cp)
page_p = (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[ft_page_st][2]}" styleIDRef="{ft_page_st}" pageBreak="0" columnBreak="0" merged="0">{auto_page}</hp:p>')
page_box = tbl_host(table([[(page_p, None, 'CENTER')]], [50.5], [22], BF_BOX_THIN), ST_HOST_F)
footer_sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
              f'linkListNextIDRef="0" textWidth="{u(666.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">'
              + page_box + P('이 문제지에 관한 저작권은 한국교육과정평가원에 있습니다.', ft_copy_st)
              + '</hp:subList>')
footer_ctrl = f'<hp:ctrl><hp:footer id="{nid()}" applyPageType="BOTH">{footer_sub}</hp:footer></hp:ctrl>'
col1 = '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0" /></hp:ctrl>'
col2 = (f'<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="2" sameSz="1" sameGap="{u(28.2)}">'
        '<hp:colLine type="SOLID" width="0.4 mm" color="#000000" /></hp:colPr></hp:ctrl>')

# ================================================================== 문항 JSON → 문서
import json
blocks = json.loads(Path(args.items).read_text(encoding='utf-8'))
FCLS = {'sin': F_SIN, 'gyeon': F_GYEON, 'gyeongo': F_GYEONGO, 'jung': F_JUNG}

def run_char(r, kind):
    # 본문(지문·보기)은 --pratio, 그 밖은 --ratio 적용. 큰 글자(발문 번호 등)는 같은 값을 쓴다.
    inbox = kind in ('passage', 'label', 'bogi', 'bogi_item', 'bogi_title')
    ratio = args.pratio if inbox else args.ratio
    spacing = args.pspacing if inbox else args.spacing
    if r['f'] in ('gyeongo', 'jung') and r['s'] > 15: ratio, spacing = 100, 0
    return char(FCLS[r['f']], r['s'], ratio, spacing, ul=r['ul'], box=r['box'])

# 상자(문단 테두리) 기하: 원본 상자 좌우 = 단 왼쪽 0 ~ 317.6, 보기 = 10.8 ~ 317.2 (단 폭 320.9)
BOXES = {'passage': dict(left=args.box_l, right=args.box_r, border=BF_BOX_THIN),
         'bogi': dict(left=10.8 + args.box_l, right=args.box_r, border=BF_BOX_THIN)}

def block_para(b, first_in_box, prev_pt):
    """블록 종류 → paraPr 인덱스"""
    t = b['type']; box = BOXES.get(b['box']) if b['box'] else None
    kw = dict(prev=prev_pt)
    if t == 'instr': return para('LEFT', line=16, nxt=0, **kw)
    if t == 'stem': return para('LEFT', left=11, indent=-11, line=18.4, nxt=0, keep_next=True, **kw)
    if t == 'choice': return para('JUSTIFY', left=21.2, indent=-10, line=18.4, **kw)
    if t == 'label': return para('LEFT', line=18.4, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'passage': return para('JUSTIFY', indent=10, line=18.4, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'bogi_title': return para('CENTER', line=18.4, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'bogi': return para('JUSTIFY', indent=10.8, line=18.4, border=box['border'], left=box['left'], right=box['right'], connect=True, **kw)
    if t == 'bogi_item': return para('JUSTIFY', left=13 + box['left'], indent=-13, line=18.4, border=box['border'], right=box['right'], connect=True, **kw)
    raise ValueError(t)

STYLE_OF = {}
def style_for(t):
    names = {'instr': ('발문 안내', 'Instruction'), 'stem': ('문항', 'Question'), 'choice': ('선택지', 'Choice'),
             'label': ('지문 구분', 'PassageLabel'), 'passage': ('지문', 'Passage'), 'bogi_title': ('보기 제목', 'BoxTitle'),
             'bogi': ('보기 본문', 'BoxBody'), 'bogi_item': ('보기 항목', 'BoxItem')}
    if t not in STYLE_OF:
        n, e = names[t]; STYLE_OF[t] = style(n, e, para('JUSTIFY', line=18.4), char())
    return STYLE_OF[t]

NAT = 6.6  # 같은 문단 안 줄 사이 자연 간격(원본 측정)
def block_xml(b, i, bl, sec_first):
    prev_b = bl[i - 1] if i else None
    t = b['type']
    gap = b['gap'] or 0
    first_in_box = b['box'] and (not prev_b or prev_b['box'] != b['box'] or prev_b['page'] != b['page'] and False)
    prev = 0 if (b['col_start'] or b['gap'] is None) else max(0, gap - NAT - (args.box_pad if first_in_box else 0))
    if t in ('choice', 'bogi', 'passage', 'bogi_item') and gap and gap < 14: prev = 0
    if t == 'stem' and prev_b and prev_b['box'] and not b['col_start']: prev = max(0, gap - NAT - args.box_pad)
    pp = block_para(b, first_in_box, round(prev, 1))
    st = style_for(t)
    spans = [(r['t'], run_char(r, t)) for r in b['runs'] if r['t']]
    cb = b['col_start'] and not sec_first and not (i and blocks[i - 1].get('spans_cols') and False)
    name, eng, pp0, cp0 = STYLES[st]
    body = ''.join(run(tx, c) for tx, c in spans)
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">'
            f'{body}</hp:p>')

# ---- 머리말(2쪽~): 짝수쪽 = 쪽번호 왼쪽 / 홀수쪽 = 쪽번호 오른쪽
ST_HOST_R = style('개체 문단(오른쪽)', 'ObjectHostRight', para('RIGHT', pct=True), char())
def boxed_r(inner_p, w, h, host):
    return tbl_host(table([[(inner_p, None, 'CENTER')]], [w], [h], BF_BOX_MID), host)
big_l = P('', ST_NORMAL)
def hdr_cell_num(n_auto, align):
    pp = para(align, line=36)
    cp = char(F_GYEON, 31.3, 100, 0)
    st = style('쪽 큰 숫자(머리말)', 'HeaderPageNum', pp, cp)
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{cp}"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" userChar="" '
            f'prefixChar="" suffixChar="" supscript="0" /></hp:autoNum></hp:ctrl><hp:t></hp:t></hp:run></hp:p>')
title_p = P('국어 영역', style('머리말 영역명', 'HeaderArea', para('CENTER', line=36), char(F_GYEONGO, 28, 100, 0)))
type_style = style('머리말 홀수형', 'HeaderType', para('CENTER', line=24), char(F_GYEONGO, 18.9, 80, -2))
def type_box(host): return boxed_r(P('홀수형', type_style), 52, 22, host)
def header_xml(parity):
    num_l = parity == 'EVEN'
    left = hdr_cell_num(0, 'LEFT') if num_l else type_box(ST_HOST)
    right = type_box(ST_HOST_R) if num_l else hdr_cell_num(0, 'RIGHT')
    tb = table([[(left, None, 'CENTER'), (title_p, None, 'CENTER'), (right, None, 'CENTER')]],
               [150, 370.4, 150], [37], BF_NONE)
    sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
           f'linkListNextIDRef="0" textWidth="{u(670.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">'
           + tbl_host(tb, ST_HOST) + '</hp:subList>')
    return f'<hp:ctrl><hp:header id="{nid()}" applyPageType="{parity}">{sub}</hp:header></hp:ctrl>'

# ---- 구역 설정(쪽 번호 시작·여백 가변)
def make_sec_pr(top_pt, start_page, header_pt):
    sp = re.sub(r'(<hp:margin header=)"\d+"( footer="\d+" gutter="0" left="\d+" right="\d+") top="\d+"', rf'\g<1>"{u(header_pt)}"\g<2> top="{u(top_pt)}"', sec_pr)
    sp = re.sub(r'(<hp:startNum pageStartsOn="BOTH" page=)"\d+"', rf'\g<1>"{start_page}"', sp)
    sp = sp.replace('<hp:pagePr landscape="WIDELY"', '<hp:pagePr landscape="WIDELY"')
    return sp

# ---- 본문 조립: 구역 0 = 1쪽(머리 표 포함), 구역 1 = 2쪽 이후(머리말 사용)
page1 = [b for b in blocks if b['page'] == 1]
rest = [b for b in blocks if b['page'] > 1]
name, eng, pp_host, cp_host = STYLES[ST_HOST]

def host_first(sec_pr_xml, extra_ctrls, content_before):
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp_host}" styleIDRef="{ST_HOST}" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{cp_host}">{sec_pr_xml}{col1}{extra_ctrls}{content_before}</hp:run></hp:p>')

def col2_run(cp): return f'<hp:run charPrIDRef="{cp}">{col2}</hp:run>'

def section_xml(sec_blocks, first_paras, top_pt, start_page, header_pt, head_content, extra_ctrls):
    out = [host_first(make_sec_pr(top_pt, start_page, header_pt), extra_ctrls, head_content)]
    for i, b in enumerate(sec_blocks):
        x = block_xml(b, i, sec_blocks, sec_first=(i == 0))
        if i == 0:   # 2단 시작 컨트롤을 첫 블록 앞에 삽입
            x = x.replace('merged="0">', 'merged="0">' + col2_run(STYLES[style_for(b["type"])][3]), 1)
        out.append(x)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><hs:sec {NS}>' + ''.join(out) + '</hs:sec>'

sec0 = section_xml(page1, None, 107.8, 1, 0, head_tbl, footer_ctrl)
sec1 = section_xml(rest, None, args.top2, 2, args.hdr2, '', footer_ctrl.replace(footer_ctrl.split('"')[1], str(nid()), 1) + header_xml('EVEN') + header_xml('ODD'))

# ================================================================== 패키지(2개 구역)
with zipfile.ZipFile(ROOT / 'work/seed_package.hwpx') as z:
    seed = {n: z.read(n) for n in z.namelist()}
head = seed['Contents/header.xml'].decode('utf-8')
def swap(tag, new):
    global head
    head, n = re.subn(rf'<hh:{tag} itemCnt="\d+">.*?</hh:{tag}>', lambda m: new, head, flags=re.S)
    assert n == 1, tag
swap('fontfaces', fontfaces()); swap('borderFills', borderfills())
swap('charProperties', charprops()); swap('paraProperties', paraprops()); swap('styles', styles_xml())
head = head.replace('secCnt="1"', 'secCnt="2"')
hpf = seed['Contents/content.hpf'].decode('utf-8')
hpf = re.sub(r'<opf:item id="image1"[^>]*/>', '', hpf)
hpf = hpf.replace('<opf:item id="settings"', '<opf:item id="section1" href="Contents/section1.xml" media-type="application/xml" />'
                  '<opf:item id="settings"', 1)
hpf = hpf.replace('<opf:itemref idref="section0" linear="yes" />', '<opf:itemref idref="section0" linear="yes" />'
                  '<opf:itemref idref="section1" linear="yes" />')
prv = '\n'.join(b['text'] for b in blocks)[:1000]
out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr(zipfile.ZipInfo('mimetype'), seed['mimetype'], compress_type=zipfile.ZIP_STORED)
    for n, data in seed.items():
        if n == 'mimetype' or n.startswith('BinData/'): continue
        if n == 'Contents/header.xml': data = head.encode('utf-8')
        elif n == 'Contents/content.hpf': data = hpf.encode('utf-8')
        elif n == 'Contents/section0.xml': data = sec0.encode('utf-8')
        elif n == 'Preview/PrvText.txt': data = prv.encode('utf-8')
        z.writestr(n, data)
    z.writestr('Contents/section1.xml', sec1.encode('utf-8'))
print('wrote', out, 'blocks', len(blocks), 'styles', len(STYLES), 'charPr', len(CHARS), 'paraPr', len(PARAS))
