"""국어 1쪽을 '문단 기반' 한글 문서로 재구성한다.
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

# ================================================================== content
SIN = char(ratio=args.pratio, spacing=args.pspacing)                       # 본문 11.2pt
BOXED = char(box=True, ratio=args.pratio, spacing=args.pspacing)             # 글자 테두리
UL = char(ul=True)                 # 밑줄
passage = (ROOT / 'scripts/p1_passage.txt').read_text(encoding='utf-8').strip().split('\n')
if args.probe:
    passage[0] += ' 편집 안정성 확인을 위해 문장을 추가합니다. 이 문장은 아래 문단을 밀어내야 합니다.'
# 첫 문단의 '단순 관점'(최초 1회)에만 글자 테두리
p0 = passage[0]; k = p0.find('단순 관점')
passage_spans = [[(p0[:k], SIN), ('단순 관점', BOXED), (p0[k + 4:], SIN)]] + [[(t, SIN)] for t in passage[1:]]
passage_xml = ''.join(P(sp, ST_BODY) for sp in passage_spans)
PASSAGE_W, PASSAGE_IN = 317.6, (8.1, 4.4, 4, 4)
passage_tbl = table([[(passage_xml, None, 'TOP')]], [PASSAGE_W], [100], BF_BOX_THIN, margin=PASSAGE_IN)

q1 = [('1. 윗글의 내용과 일치하지 ', char(F_GYEON, 12.7, None, None)), ('않는', char(F_GYEON, 12.7, None, None, ul=True)),
      (' 것은?', char(F_GYEON, 12.7, None, None))]
c1 = ['①단순 관점에 따르면 추론하기는 언어 이해에 해당한다.',
      '②단순 관점은 해독의 발달과 언어 이해의 발달을 모두 고려하여 독자 유형을 나눈다.',
      '③단순 관점에 따르면 독해 능력이 발달되기 위해서는 말소리 듣기 경험에 앞서 독서 경험이 필요하다.',
      '④단순 관점은 해독과 언어 이해가 독해 능력에 끼치는 영향을 밝혀 독해 능력 연구의 기반을 마련하였다.',
      '⑤단순 관점과 달리, 독해에 영향을 주는 여러 요소를 고려하여 독해 능력을 복잡한 과정으로 설명한 연구들이 있다.']
q2 = [('2. ', char(F_GYEON, 12.7, None, None)), ('단순 관점', char(F_SIN, 11.2, box=True)),
      ('에 대한 비판으로 가장 적절한 것은?', char(F_SIN, 11.2))]
c2 = ['①해독이 부족하여 글의 내용을 잘 이해하지 못하는 경우를 다루지 않았다.',
      '②독해에서 어려움이 나타날 수 있음을 고려하지 않아 독해를 지나치게 단순화하였다.',
      '③독해 능력 발달에 있어 해독의 영향이 더 크다고 보아 언어 이해의 중요성을 고려하지 않았다.',
      '④해독 발달을 글을 통한 시각적 경험으로만 설명하여 청각적 경험의 필요성을 증명하지 못하였다.',
      '⑤해독과 언어 이해를 바탕으로 글의 의미를 이해하기까지의 사고 과정이 어떻게 이루어지는지 밝히지 않았다.']
G = lambda ul=False: char(F_GYEON, 12.7, None, None, ul=ul)
q3 = [('3. 윗글을 바탕으로 <보기>를 이해한 내용으로 적절하지 ', G()), ('않은', G(True)), (' 것은? [3점]', G())]
bogi = ['단순 관점을 지지하는 연구자 갑은 학생 A, B의 독해 능력을 분석하기 위한 활동을 진행하였다. 활동은 학생 A, B와 같은 연령대의 학생들이 수행하기에 무리가 없는 수준의 자료로 진행되었다. 아래는 학생 A, B가 수행한 활동의 결과이다.']
bogi_items = ['◦소리 내어 단어 읽기: 학생 A는 활동 자료에 있는 단어를 빠르고 정확하게 소리 내어 읽었고 한눈에 잘 식별하였다. 학생 B는 활동 자료에 있는 단어를 올바르게 발음하지 못하였고 한눈에 식별하지 못하였다.',
              '◦중심 내용 파악하기: 학생 A는 활동 자료를 글로 읽을 때와 말로 들을 때 모두 중심 내용을 파악하지 못하였다. 학생 B는 활동 자료를 글로 읽을 때는 중심 내용을 파악하지 못했지만 말로 들을 때는 중심 내용을 파악하였다.']
c3 = ['①갑은 학생 A가 해독은 발달되었지만, 중심 내용을 파악하지 못한 점에서 언어 이해가 부족하다고 생각하겠군.',
      '②갑은 학생 A가 글자와 글자 소리에 대한 학습을 통해 개별 단어를 인식하는 능력이 발달되었다고 생각하겠군.',
      '③갑은 학생 A의 언어 이해가 구어 의사소통 경험뿐 아니라 글 읽기 경험을 통해서도 발달될 수 있다고 생각하겠군.',
      '④갑은 학생 B가 단어를 올바르게 발음하지는 못하지만, 글 읽기 경험을 통해 중심 내용은 파악할 수 있게 되었다고 생각하겠군.',
      '⑤갑은 학생 B가 단어를 한눈에 식별하지는 못하지만 말로 들은 활동 자료의 중심 내용을 파악할 수 있었던 것은, 해독 발달 전에 언어 이해가 발달되었기 때문이라고 생각하겠군.']
bogi_xml = (P('<보 기>', ST_BOXTITLE) + ''.join(P(t, ST_BOX) for t in bogi)
            + ''.join(P(t, ST_BULLET) for t in bogi_items))
bogi_tbl = table([[(bogi_xml, None, 'TOP')]], [306.2], [100], BF_BOX_THIN, margin=(8.2, 4, 3, 4))

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

# ---- 본문 조립
name, eng, pp_host, cp_host = STYLES[ST_HOST]
first_p = (f'<hp:p id="{nid()}" paraPrIDRef="{pp_host}" styleIDRef="{ST_HOST}" pageBreak="0" columnBreak="0" merged="0">'
           f'<hp:run charPrIDRef="{cp_host}">{sec_pr}{col1}{footer_ctrl}{head_tbl}</hp:run></hp:p>')
# 2단 시작: 안내문 문단의 첫 run 앞에 단 정의
instr = P('[1～3] 다음 글을 읽고 물음에 답하시오.', ST_INSTR,
          extra_first=f'<hp:run charPrIDRef="{STYLES[ST_INSTR][3]}">{col2}</hp:run>')
left = [instr, tbl_host(passage_tbl, ST_HOST), P(q1, ST_STEM)] + [P(c, ST_CHOICE) for c in c1]
q3_style = style('문항(빈 여백 뒤)', 'QuestionAfterSpace', para('LEFT', left=11, indent=-11, line=18.4, prev=70, nxt=6, keep_next=True),
                 char(F_GYEON, 12.7, None, None))
right = [P(q2, ST_STEM, col_break=True)] + [P(c, ST_CHOICE) for c in c2] + [P(q3, q3_style),
         tbl_host(bogi_tbl, ST_HOST_IND)] + [P(c, ST_CHOICE) for c in c3]
# ST_STEM의 prev=14가 단 맨 위에 올 때를 위한 별도 스타일은 쓰지 않고, 오른쪽 첫 문항은 prev 0으로 별도 정의
q2_style = style('문항(단 첫머리)', 'QuestionTop', para('LEFT', left=11, indent=-11, line=18.4, prev=0, nxt=6, keep_next=True),
                 char(F_GYEON, 12.7, None, None))
right[0] = P(q2, q2_style, col_break=True)
section = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><hs:sec {NS}>'
           + first_p + ''.join(left) + ''.join(right) + '</hs:sec>')

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
hpf = seed['Contents/content.hpf'].decode('utf-8')
hpf = re.sub(r'<opf:item id="image1"[^>]*/>', '', hpf)
hpf = hpf.replace('<opf:item id="header"', '<opf:item id="header"', 1)
prv = '\n'.join(re.sub(r'<[^>]+>', '', t) for t in re.findall(r'<hp:t>.*?</hp:t>', section))[:1000]
out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr(zipfile.ZipInfo('mimetype'), seed['mimetype'], compress_type=zipfile.ZIP_STORED)
    for n, data in seed.items():
        if n in ('mimetype',) or n.startswith('BinData/'): continue
        if n == 'Contents/header.xml': data = head.encode('utf-8')
        elif n == 'Contents/content.hpf': data = hpf.encode('utf-8')
        elif n == 'Contents/section0.xml': data = section.encode('utf-8')
        elif n == 'Preview/PrvText.txt': data = prv.encode('utf-8')
        z.writestr(n, data)
print('wrote', out, 'styles', len(STYLES), 'charPr', len(CHARS), 'paraPr', len(PARAS))
