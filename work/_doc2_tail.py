# ================================================================== 문항 JSON → 문서 (v2)
import json, statistics
blocks = json.loads(Path(args.items).read_text(encoding='utf-8'))
FCLS = {'sin': F_SIN, 'gyeon': F_GYEON, 'gyeongo': F_GYEONGO, 'jung': F_JUNG, 'times': F_TIMES, 'sgraphic': F_JUNG}

def run_char(r, kind):
    inbox = kind in ('passage', 'label', 'bogi', 'bogi_item', 'bogi_title', 'notice')
    ratio = args.pratio if inbox else args.ratio
    spacing = args.pspacing if inbox else args.spacing
    if r['f'] == 'times': ratio, spacing = 100, 0
    if r['f'] in ('gyeongo', 'jung') and r['s'] > 15: ratio, spacing = 100, 0
    return char(FCLS[r['f']], r['s'], ratio, spacing, bold=r.get('b', False), ital=r.get('i', False), ul=r['ul'], box=r['box'])

BOXES = {'passage': dict(left=args.box_l, right=args.box_r, border=BF_BOX_THIN),
         'notice': dict(left=args.box_l, right=args.box_r, border=BF_BOX_THIN),
         'bogi': dict(left=10.8 + args.box_l, right=args.box_r, border=BF_BOX_THIN)}

# 종류별 기본 줄 간격: 여러 줄 블록의 pitch 중앙값, 없으면 18.4
_p = {}
for b in blocks:
    if b.get('pitch'): _p.setdefault(b['type'], []).append(b['pitch'])
PITCH = {t: round(statistics.median(v), 1) for t, v in _p.items()}
def pitch_of(b): return b.get('pitch') or PITCH.get(b['type']) or (17.2 if args.lang == 'en' else 18.4)

def block_para(b, prev_pt):
    t = b['type']; box = BOXES.get(b['box']) if b['box'] else None
    ln = pitch_of(b); kw = dict(prev=prev_pt)
    if t == 'instr': return para('LEFT', line=16, **kw)
    if t == 'stem': return para('LEFT', left=11, indent=-11, line=ln, keep_next=True, **kw)
    if t == 'choice': return para('JUSTIFY', left=21.2, indent=-10, line=ln, **kw)
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
    if t == 'bogi_item': return para('JUSTIFY', left=13 + box['left'], indent=-13, line=ln, border=box['border'], right=box['right'], connect=True, **kw)
    raise ValueError(t)

STYLE_OF = {}
def style_for(t):
    names = {'instr': ('발문 안내', 'Instruction'), 'stem': ('문항', 'Question'), 'choice': ('선택지', 'Choice'),
             'choice_row': ('선택지(가로)', 'ChoiceRow'), 'footnote': ('각주', 'Footnote'), 'dialogue': ('대화 빈칸', 'DialogueBlank'),
             'notice': ('안내 상자', 'NoticeBox'), 'label': ('지문 구분', 'PassageLabel'), 'passage': ('지문', 'Passage'),
             'bogi_title': ('보기 제목', 'BoxTitle'), 'bogi': ('보기 본문', 'BoxBody'), 'bogi_item': ('보기 항목', 'BoxItem'),
             'figure': ('그림', 'Figure'), 'table': ('표', 'Table')}
    if t not in STYLE_OF:
        n, e = names[t]; STYLE_OF[t] = style(n, e, para('JUSTIFY', line=18.4), char())
    return STYLE_OF[t]

IMAGES = []   # (id, path)
def pic_xml(b):
    n = len(IMAGES) + 1; IMAGES.append((f'image{n}', b['png']))
    W, H = u(b['w']), u(b['h'])
    return (f'<hp:pic id="{nid()}" zOrder="0" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
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
            '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
            'horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
            '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:shapeComment>시험지 그림</hp:shapeComment></hp:pic>')

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
def block_xml(b, i, bl, sec_first):
    prev_b = bl[i - 1] if i else None
    t = b['type']; gap = b['gap'] or 0
    nat = (pitch_of(b) - b['h']) if b.get('h') else NAT_KO
    first_in_box = b['box'] and (not prev_b or prev_b['box'] != b['box'])
    prev = 0 if (b['col_start'] or b['gap'] is None) else max(0, gap - nat - (args.box_pad if first_in_box else 0))
    if t in ('choice', 'bogi', 'passage', 'bogi_item', 'choice_row', 'footnote') and gap and gap < 14 and b['box'] == (prev_b or {}).get('box'): prev = 0
    if t == 'stem' and prev_b and prev_b['box'] and not b['col_start']: prev = max(0, gap - nat - args.box_pad)
    cb = b['col_start'] and not sec_first
    prev = round(prev, 1)
    if t == 'figure':
        pp = para('LEFT', left=b['x0'], pct=True, prev=prev)
        st = style_for('figure'); cp0 = STYLES[st][3]
        return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="{1 if cb else 0}" merged="0">'
                f'<hp:run charPrIDRef="{cp0}">{pic_xml(b)}</hp:run></hp:p>')
    if t == 'table':
        cap, tb = table_xml(b, prev)
        host = tbl_host(tb, ST_HOST)
        if cb and cap: cap = cap.replace('columnBreak="0"', 'columnBreak="1"', 1)
        return cap + host
    pp = block_para(b, prev); st = style_for(t)
    runs = b['runs']
    if t == 'footnote': runs = [dict(r, t=r['t'].replace('\t', '   ')) for r in runs]
    spans = [(r['t'], run_char(r, t)) for r in runs if r['t']]
    body = ''.join(run(tx, c) for tx, c in spans)
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
def host_first(sec_pr_xml, extra_ctrls, content_before):
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp_host}" styleIDRef="{ST_HOST}" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{cp_host}">{sec_pr_xml}{col1}{extra_ctrls}{content_before}</hp:run></hp:p>')
def col2_run(cp): return f'<hp:run charPrIDRef="{cp}">{col2}</hp:run>'
def section_xml(sec_blocks, top_pt, start_page, header_pt, head_content, extra_ctrls):
    out = [host_first(make_sec_pr(top_pt, start_page, header_pt), extra_ctrls, head_content)]
    for i, b in enumerate(sec_blocks):
        x = block_xml(b, i, sec_blocks, sec_first=(i == 0))
        if i == 0:
            stt = style_for(b['type']) if b['type'] not in ('table',) else style_for('table')
            x = x.replace('merged="0">', 'merged="0">' + col2_run(STYLES[stt][3]), 1)
        out.append(x)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><hs:sec {NS}>' + ''.join(out) + '</hs:sec>'

sec0 = section_xml(pages_first, 107.8, 1, 0, head_tbl, footer_ctrl)
sec1 = section_xml(rest, args.top2, 2, args.hdr2, '', footer_ctrl.replace(footer_ctrl.split('"')[1], str(nid()), 1) + header_xml('EVEN') + header_xml('ODD')) if rest else None

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
if sec1: head = head.replace('secCnt="1"', 'secCnt="2"')
hpf = seed['Contents/content.hpf'].decode('utf-8')
hpf = re.sub(r'<opf:item id="image1"[^>]*/>', '', hpf)
items = ''.join(f'<opf:item id="{iid}" href="BinData/{iid}.png" media-type="image/png" isEmbeded="1" />' for iid, _ in IMAGES)
if sec1: items = '<opf:item id="section1" href="Contents/section1.xml" media-type="application/xml" />' + items
hpf = hpf.replace('<opf:item id="settings"', items + '<opf:item id="settings"', 1)
if sec1: hpf = hpf.replace('<opf:itemref idref="section0" linear="yes" />', '<opf:itemref idref="section0" linear="yes" /><opf:itemref idref="section1" linear="yes" />')
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
    if sec1: z.writestr('Contents/section1.xml', sec1.encode('utf-8'))
    for iid, path in IMAGES: z.write(ROOT / path, f'BinData/{iid}.png')
print('wrote', out, 'blocks', len(blocks), 'styles', len(STYLES), 'charPr', len(CHARS), 'paraPr', len(PARAS), 'images', len(IMAGES))
