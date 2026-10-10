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
ap.add_argument('--out', default=str(ROOT / 'output/native_p1/국어_1페이지_네이티브.hwpx'))
ap.add_argument('--ratio', type=int, default=95)
ap.add_argument('--spacing', type=int, default=-2)
ap.add_argument('--pratio', type=int, default=None)
ap.add_argument('--pspacing', type=int, default=None)
ap.add_argument('--footer', type=float, default=0)
ap.add_argument('--nonlatin', default='BREAK_WORD')
ap.add_argument('--probe', action='store_true', help='첫 지문 문단에 문장을 추가한 편집 시험본')
args = ap.parse_args()
if args.pratio is None: args.pratio = args.ratio
if args.pspacing is None: args.pspacing = args.spacing

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
def para(align='JUSTIFY', left=0, indent=0, right=0, line=18.4, prev=0, nxt=0, border=None, keep_next=False, pct=False):
    key = (align, left, indent, right, line, prev, nxt, border, keep_next, pct)
    if key not in PARAS: PARAS.append(key)
    return PARAS.index(key)
def paraprops():
    out = []
    for i, (align, left, indent, right, line, prev, nxt, border, keep_next, pct) in enumerate(PARAS):
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
            f'<hh:border borderFillIDRef="{border or BF_NONE2}" offsetLeft="{u(3) if border else 0}" '
            f'offsetRight="{u(3) if border else 0}" offsetTop="{u(2) if border else 0}" '
            f'offsetBottom="{u(2) if border else 0}" connect="0" ignoreMargin="0" /></hh:paraPr>')
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

