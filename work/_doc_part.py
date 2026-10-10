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
type_style = style('머리말 홀수형', 'HeaderType', para('CENTER', line=24), char(F_GYEONGO, 18.9, 100, 0))
def type_box(host): return boxed_r(P('홀수형', type_style), 49, 22, host)
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
    sp = sec_pr.replace('top="{u(107.8)}"', '')  # (no-op; sec_pr is already rendered text)
    sp = re.sub(r'top="\d+"', f'top="{u(top_pt)}"', sp)
    sp = re.sub(r'header="\d+"', f'header="{u(header_pt)}"', sp)
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
