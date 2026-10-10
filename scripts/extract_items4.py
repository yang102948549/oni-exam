"""PDF 시험지 → 문항 블록 JSON (국어·영어 공통).
usage: python -X utf8 scripts/extract_items2.py PDF FIRST LAST OUT.json [--lang ko|en] [--figdir DIR]
블록 type: instr label passage stem choice choice_row footnote notice dialogue bogi_title bogi bogi_item figure table
"""
import argparse, json, re, sys
from pathlib import Path
import pymupdf
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mathpage

ap = argparse.ArgumentParser()
ap.add_argument('--math', action='store_true'); ap.add_argument('pdf'); ap.add_argument('first', type=int); ap.add_argument('last', type=int); ap.add_argument('out')
ap.add_argument('--lang', default='ko'); ap.add_argument('--figdir', default='work/figs')
A = ap.parse_args()
MID, CIRC = 421.0, '①②③④⑤'
Path(A.figdir).mkdir(parents=True, exist_ok=True)

def fclass(name):
    n = name or ''
    if n == 'EQ': return 'eq'
    if 'TimesNewRoman' in n or 'Times' in n: return 'times'
    if '°ß°íµñ' in n: return 'gyeongo'
    if '°ß¸íÁ¶' in n or '°ß¸í' in n: return 'gyeon'
    if '°íµñ' in n or 'Gulim' in n or '³ª·ç' in n or 'Haansoft' in n: return 'jung'
    return 'sin'

def hsegs(page):
    out = []
    for d in page.get_drawings():
        for it in d['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.2 and abs(a.x - b.x) > 3: out.append((min(a.x, b.x), max(a.x, b.x), a.y, d.get('width') or 0))
    return out

def vlines(page):
    v = []
    for d in page.get_drawings():
        for it in d['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.x - b.x) < 0.2 and abs(a.y - b.y) > 4: v.append([round((a.x + b.x) / 2, 1), min(a.y, b.y), max(a.y, b.y)])
    v.sort(); out = []
    for x, y0, y1 in v:
        for o in out:
            if abs(o[0] - x) < 0.6 and y0 <= o[2] + 3 and y1 >= o[1] - 3: o[1] = min(o[1], y0); o[2] = max(o[2], y1); break
        else: out.append([x, y0, y1])
    return out

def find_boxes(page):
    vl = [v for v in vlines(page) if v[2] - v[1] > 25]; boxes = []
    for a in vl:
        for b in vl:
            if b[0] - a[0] > 120 and abs(a[1] - b[1]) < 4 and abs(a[2] - b[2]) < 4:
                bx = (a[0], a[1], b[0], a[2])
                if not any(abs(bx[i] - o[i]) < 2 for o in boxes for i in range(1)) or bx not in boxes: boxes.append(bx)
    return boxes

def marks(line, segs):
    x0, y0, x1, y1 = line['bbox']; ul, box = [], []
    for sx0, sx1, sy, w in segs:
        if sx1 < x0 - 1 or sx0 > x1 + 1 or sx1 - sx0 > 330: continue
        if 0.44 <= w <= 0.6 and y1 - 4 <= sy <= y1 + 3: ul.append((sx0, sx1))
    tops = [s for s in segs if abs(s[3] - 0.36) < 0.05 and y0 - 4 <= s[2] <= y0 + 3 and s[1] - s[0] < 130 and x0 - 4 <= s[0] and s[1] <= x1 + 6]
    bots = [s for s in segs if abs(s[3] - 0.36) < 0.05 and y1 - 3 <= s[2] <= y1 + 4 and s[1] - s[0] < 130]
    for t in tops:
        for b in bots:
            if abs(t[0] - b[0]) < 0.5 and abs(t[1] - b[1]) < 0.5 and 8 < b[2] - t[2] < 20: box.append((t[0], t[1]))
    return ul, list({(round(a, 1), round(b, 1)) for a, b in box})

def runs_of(rl, ul, box):
    runs = []
    for sp in rl['spans']:
        fc, sz = fclass(sp['font']), round(sp['size'], 1)
        fn = sp['font'] or ''
        bold, ital = ('Bold' in fn), ('Italic' in fn)
        for ch in sp['chars']:
            cx = (ch['bbox'][0] + ch['bbox'][2]) / 2
            u = any(a - 0.5 <= cx <= b + 0.5 for a, b in ul); bx = any(a - 0.5 <= cx <= b + 0.5 for a, b in box)
            key = (fc, sz, u, bx, bold, ital)
            if runs and runs[-1][0] == key: runs[-1][1] += ch['c']
            else: runs.append([key, ch['c']])
    out = []
    for k, t in runs:
        r = {'t': t, 'f': k[0], 's': k[1], 'ul': k[2], 'box': k[3], 'b': k[4], 'i': k[5]}
        if k[0] == 'eq' and t in mathpage.EQ: r['eq'] = mathpage.EQ[t]
        out.append(r)
    return out

def line_adv(rl):
    a = []
    for sp in rl['spans']:
        ch = sp['chars']
        for c1, c2 in zip(ch, ch[1:]):
            if '가' <= c1['c'] <= '힣' and '가' <= c2['c'] <= '힣': a.append(c2['origin'][0] - c1['origin'][0])
    if len(a) < 5: return None
    a.sort(); return a[len(a) // 4]

def line_tr(rl):
    r = []
    for sp in rl['spans']:
        if fclass(sp['font']) != 'times': continue
        t = ''.join(c['c'] for c in sp['chars'])
        if len(t.strip()) < 12: continue
        w = pymupdf.get_text_length(t, fontname='tiro', fontsize=sp['size'])
        if w > 0: r.append((sp['bbox'][2] - sp['bbox'][0]) / w)
    return min(r) if r else None

def trim(runs):
    while runs and not runs[-1]['t'].strip(): runs.pop()
    if runs: runs[-1]['t'] = runs[-1]['t'].rstrip()
    while runs and not runs[0]['t'].strip(): runs.pop(0)
    if runs: runs[0]['t'] = runs[0]['t'].lstrip()
    return runs
def txt(runs): return ''.join(r['t'] for r in runs)
def sp_run(): return {'t': ' ', 'f': 'sin', 's': 11.2, 'ul': False, 'box': False, 'b': False, 'i': False}

doc = pymupdf.open(A.pdf)
blocks = []
cur = None; zone = None
def flush():
    global cur
    if cur:
        xs = cur.pop('_xs', [])
        if len(xs) > 1:
            import statistics as st0
            cur['fx'] = round(xs[0], 1); cur['cx'] = round(st0.median(xs[1:]), 1)
        ys = cur.pop('_ys', []); ad = cur.pop('_adv', [])
        if ad: cur['adv'] = round(min(ad), 2)
        tr_ = cur.pop('_tr', [])
        if tr_: cur['tr'] = round(min(tr_), 3)
        if len(ys) >= 2:
            import statistics as st
            cur['pitch'] = round(st.median([b[0] - a[0] for a, b in zip(ys, ys[1:])]), 1)
        if ys:
            import statistics as st
            cur['h'] = round(st.median([y[1] - y[0] for y in ys]), 1)
        blocks.append(cur); cur = None

for pn in range(A.first - 1, A.last):
    page = doc[pn]; segs = hsegs(page); raw = page.get_text('rawdict')
    fig_rects = []; gtabs_all = []
    if A.math:
        imgs = [pymupdf.Rect(i['bbox']) for i in page.get_image_info()]
        fig_rects = [r for r in mathpage.figure_regions(page) if not any(r.intersects(i) and (r & i).get_area() > 0.4 * min(r.get_area(), i.get_area()) for i in imgs)]
        gtabs_all = mathpage.find_grid_tables(page, top=(245 if A.lang == 'soc' and pn == 0 else 150))
        fig_rects = [r for r in fig_rects if not any((r & g['rect']).get_area() > 0.5 * min(r.get_area(), g['rect'].get_area()) for g in gtabs_all)]
        raw = mathpage.prepare(page, fig_rects + [i for i in imgs if i.y1 > 215], grid_rects=gtabs_all)
    top = (245 if A.lang == 'soc' else 225) if pn == 0 else 150
    boxes = find_boxes(page) if A.lang == 'soc' else []
    def box_of(y0, x0):
        for i, bx in enumerate(boxes):
            if bx[0] - 3 <= x0 <= bx[2] and bx[1] - 9 <= y0 <= bx[3]: return i
        return None
    # ---- 그림: 머리 제목 이미지(y<150 또는 쪽 상단 큰 제목)는 제외
    figs = []
    for k, im in enumerate(page.get_image_info()):
        x0, y0, x1, y1 = im['bbox']
        if y1 < 215 and (x1 - x0) < 200: continue          # '국어/영어 영역' 제목 이미지
        if (y1 - y0) < 20: continue
        figs.append(['figure', x0, y0, x1, y1, k])
    figs.sort(key=lambda f: f[2]); merged = []
    for f in figs:
        if merged and abs(f[1] - merged[-1][1]) < 3 and f[2] <= merged[-1][4] + 6: merged[-1][4] = max(merged[-1][4], f[4])
        else: merged.append(f)
    merged += [['figure', r.x0, r.y0, r.x1, r.y1, 100 + i] for i, r in enumerate(fig_rects)]
    merged.sort(key=lambda f: f[2])
    # 서로 겹치는 그림(이미지와 도형 군집, 상자와 이미지)은 큰 것 하나만 남긴다
    keep = []
    for f in sorted(merged, key=lambda f: -((f[3] - f[1]) * (f[4] - f[2]))):
        fr = pymupdf.Rect(f[1], f[2], f[3], f[4])
        if any((fr & pymupdf.Rect(k[1], k[2], k[3], k[4])).get_area() > 0.5 * fr.get_area() for k in keep): continue
        keep.append(f)
    merged = sorted(keep, key=lambda f: f[2])
    figs = []; textbox_regions = []
    for f in merged:
        nlines = sum(1 for b in raw['blocks'] if b['type'] == 0 for l in b['lines'] if f[2] - 2 <= l['bbox'][1] and l['bbox'][3] <= f[4] + 2 and f[1] - 3 <= l['bbox'][0] <= f[3] and ''.join(c['c'] for sp in l['spans'] for c in sp['chars']).strip())
        if A.lang in ('soc', 'math'):
            cx, cy = (f[1] + f[3]) / 2, (f[2] + f[4]) / 2
            for bx in boxes:
                if bx[0] <= cx <= bx[2] and bx[1] <= cy <= bx[3]: f[1], f[2], f[3], f[4] = bx[0] - 0.5, bx[1] - 0.5, bx[2] + 0.5, bx[3] + 0.5; break
            figs.append(f)
        elif nlines >= 3: textbox_regions.append(tuple(f[1:5]))
        else: figs.append(f)
    _keep = []
    for f in sorted(figs, key=lambda f: -((f[3] - f[1]) * (f[4] - f[2]))):
        fr = pymupdf.Rect(f[1], f[2], f[3], f[4])
        if any((fr & pymupdf.Rect(k[1], k[2], k[3], k[4])).get_area() > 0.5 * fr.get_area() for k in _keep): continue
        _keep.append(f)
    figs = sorted(_keep, key=lambda f: f[2])
    if A.math:   # 같은 높이에 나란히 놓인 그림(도식+표 등)은 하나의 그림으로 합친다
        changed = True
        while changed:
            changed = False
            for i in range(len(figs)):
                for j in range(i + 1, len(figs)):
                    f, g = figs[i], figs[j]
                    same_col = ((f[1] + f[3]) / 2 >= MID) == ((g[1] + g[3]) / 2 >= MID)
                    vov = min(f[4], g[4]) - max(f[2], g[2])
                    hgap = max(f[1], g[1]) - min(f[3], g[3])
                    if same_col and vov > 0.4 * min(f[4] - f[2], g[4] - g[2]) and hgap < 45:
                        f[1], f[2], f[3], f[4] = min(f[1], g[1]), min(f[2], g[2]), max(f[3], g[3]), max(f[4], g[4]); figs.pop(j); changed = True; break
                if changed: break
    gtabs_all = [g for g in gtabs_all if not any((g['rect'] & pymupdf.Rect(f[1], f[2], f[3], f[4])).get_area() > 0.7 * g['rect'].get_area() for f in figs)]
    tagboxes = []
    if A.math:
        hs = [(round(a[0], 1), round(a[1], 1), round(a[2], 1)) for a in segs if 60 < a[1] - a[0] < 200 and top < a[2] < 1075]
        for a in hs:
            for b in hs:
                if abs(a[0] - b[0]) < 1 and abs(a[1] - b[1]) < 1 and 14 < b[2] - a[2] < 40: tagboxes.append((a[0], a[2], a[1], b[2]))
        tagboxes = list({t: 1 for t in tagboxes})
    # ---- 표: 단 안에 긴 수평선 3개 이상(2.2 kind 시험지의 표)
    tables = []
    for col in (0, 1):
        cl, cr = (88, 410) if col == 0 else (437, 758)
        rules = sorted({round(s[2], 1) for s in segs if s[0] >= cl - 3 and s[1] <= cr + 3 and (s[1] - s[0]) > 200 and 0.5 <= s[3] <= 1.4 and top < s[2] < 1075})
        if len(rules) >= 3 and rules[-1] - rules[0] < 200: tables.append((col, rules))
    # ---- 줄 수집(단별)
    def in_textbox(y0, x0):
        return any(r[1] - 2 <= y0 <= r[3] and r[0] - 3 <= x0 <= r[2] for r in textbox_regions)
    def region_excluded(y0, y1, x0):
        for f in figs:
            if f[2] - 2 <= y0 and y1 <= f[4] + 2 and f[1] - 3 <= x0 <= f[3]: return True
        return False
    for col in (0, 1):
        colL = 88.0 if col == 0 else 437.0
        L = []
        for b in raw['blocks']:
            if b['type']: continue
            for l in b['lines']:
                x0, y0, x1, y1 = l['bbox']
                if not (top < y0 < 1075) or (x0 >= MID) != bool(col): continue
                if region_excluded(y0, y1, x0): continue
                rr = trim(runs_of(l, *marks(l, segs)))
                if rr: L.append({'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1, 'runs': rr, 'adv': line_adv(l), 'tr': line_tr(l)})
        L.sort(key=lambda l: (round(l['y0'] / 3), l['x0']))
        # 표 영역 줄 분리
        tbl = next((t for t in tables if t[0] == col), None)
        tbl_lines = []
        if tbl:
            ylo, yhi = tbl[1][0] - 24, tbl[1][-1] + 3
            tbl_lines = [l for l in L if ylo <= l['y0'] <= yhi]
            L = [l for l in L if not (ylo <= l['y0'] <= yhi)]
        gtabs = [g for g in gtabs_all if ((g['rect'].x0 + g['rect'].x1) / 2 >= MID) == bool(col)]
        gt_lines = {id(g): [] for g in gtabs}
        for g in gtabs:
            inside = [l for l in L if g['rect'].x0 - 1 <= (l['x0'] + l['x1']) / 2 <= g['rect'].x1 + 1 and g['rect'].y0 - 1 <= (l['y0'] + l['y1']) / 2 <= g['rect'].y1 + 1]
            gt_lines[id(g)] = inside
            L = [l for l in L if l not in inside]
        # 같은 y 줄 병합(선택지 가로 배치, 각주)
        rows = []
        _bands = []
        for l in sorted(L, key=lambda l: l['y0']):
            if _bands and abs(_bands[-1][0] - l['y0']) < 3.0: _bands[-1][1].append(l)
            else: _bands.append([l['y0'], [l]])
        _ordered = [l for _, grp in _bands for l in sorted(grp, key=lambda l: l['x0'])]
        for l in _ordered:
            if rows and abs(rows[-1]['y0'] - l['y0']) < 3.0 and l['x0'] > rows[-1]['x1'] - 1:
                r = rows[-1]
                if l['x0'] - r['x1'] < 12:
                    last = r['segs'][-1]; last['runs'] = last['runs'] + ([sp_run()] if l['x0'] - last['x1'] >= 2.0 else []) + l['runs']; last['x1'] = l['x1']
                else: r['segs'].append(l)
                r['x1'] = l['x1']; r['y1'] = max(r['y1'], l['y1'])
                if l['adv'] is not None: r['adv'] = l['adv'] if r['adv'] is None else min(r['adv'], l['adv'])
                if l['tr'] is not None: r['tr'] = l['tr'] if r['tr'] is None else min(r['tr'], l['tr'])
            else:
                rows.append({'y0': l['y0'], 'y1': l['y1'], 'x0': l['x0'], 'x1': l['x1'], 'segs': [l], 'adv': l['adv'], 'tr': l['tr']})
        items = [('line', r) for r in rows]
        for f in figs:
            fx = (f[1] + f[3]) / 2
            if (fx >= MID) == bool(col): items.append(('fig', f))
        if tbl: items.append(('tbl', (tbl, tbl_lines)))
        for g in gtabs: items.append(('gtbl', (g, gt_lines[id(g)])))
        def ykey(it):
            if it[0] == 'gtbl': return it[1][0]['rect'].y0
            if it[0] == 'line': return it[1]['y0']
            if it[0] == 'fig': return it[1][2]
            return it[1][0][1][0] - 24
        items.sort(key=ykey)
        first_in_col = True; prev_y1 = None; prev_x0 = 0; float_bottom = None
        # 기준 x(문단 첫줄 들여쓰기 판정): 같은 단의 본문 줄 중 최소 x0
        body_x = [r['x0'] for k, r in items if k == 'line' and not re.match(r'^(\[\d|\d+\.\s|[①-⑤]|\*|<보)', txt(r['segs'][0]['runs'])) and (r['x1'] - r['x0']) > 150]
        for kind_i, it in items:
            if kind_i == 'fig':
                f = it
                # 글과 나란히 놓인 그림(글줄이 그림 옆에 있거나 다른 그림과 좌우로 겹침)은 떠 있는 개체로 만든다
                ov = [r for r in rows if r['y1'] > f[2] + 2 and r['y0'] < f[4] - 2 and (r['x1'] <= f[1] + 3 or r['x0'] >= f[3] - 3)]
                hh = f[4] - f[2]
                pair = [g for g in figs if g is not f and ((g[1] + g[3]) / 2 >= MID) == bool(col) and (g[3] <= f[1] + 3 or g[1] >= f[3] - 3)
                        and min(g[4], f[4]) - max(g[2], f[2]) > 0.4 * min(g[4] - g[2], hh)]
                gt_pair = [g for g in gtabs if (g['rect'].x1 <= f[1] + 3 or g['rect'].x0 >= f[3] - 3) and min(g['rect'].y1, f[4]) - max(g['rect'].y0, f[2]) > 0.4 * min(g['rect'].height, hh)]
                is_float = A.math and bool(ov or pair or gt_pair)
                if is_float: float_bottom = max(float_bottom or 0, f[4])
                if not is_float: flush()
                png = Path(A.figdir) / f'fig_p{pn + 1}_{f[5]}.png'
                page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(f[1], f[2], f[3], f[4])).save(png)
                gap = None if prev_y1 is None else round(f[2] - prev_y1, 1)
                blocks.append({'type': 'figure', 'page': pn + 1, 'col': col, 'y0': round(f[2], 1), 'w': round(f[3] - f[1], 1), 'h': round(f[4] - f[2], 1),
                               'x0': round(f[1] - colL, 1), 'png': str(png).replace(chr(92), '/'), 'gap': gap, 'col_start': first_in_col, 'box': None, 'runs': [], 'text': '[그림]', 'fx0': round(f[1], 1), 'float': is_float})
                if not is_float:
                    first_in_col = False; prev_y1 = f[4]
                continue
            if kind_i == 'gtbl':
                g, tl = it
                xs, ys, R = g['xs'], g['ys'], g['rect']
                cells = [[[] for _ in range(len(xs) - 1)] for _ in range(len(ys) - 1)]
                for l in sorted(tl, key=lambda l: (round(l['y0'] / 3), l['x0'])):
                    cx, cy = (l['x0'] + l['x1']) / 2, (l['y0'] + l['y1']) / 2
                    ci = max(0, min(len(xs) - 2, next((i for i in range(len(xs) - 1) if xs[i] - 1 <= cx < xs[i + 1] + 1), 0)))
                    ri = max(0, min(len(ys) - 2, next((i for i in range(len(ys) - 1) if ys[i] - 1 <= cy < ys[i + 1] + 1), 0)))
                    cells[ri][ci].extend(([sp_run()] if cells[ri][ci] else []) + l['runs'])
                ovr = [r for r in rows if r['y1'] > R.y0 + 2 and r['y0'] < R.y1 - 2 and (r['x1'] <= R.x0 + 3 or r['x0'] >= R.x1 - 3)]
                fpair = [f for f in figs if ((f[1] + f[3]) / 2 >= MID) == bool(col) and (f[3] <= R.x0 + 3 or f[1] >= R.x1 - 3) and min(f[4], R.y1) - max(f[2], R.y0) > 0.4 * min(f[4] - f[2], R.height)]
                gfloat = bool(ovr or fpair)
                if gfloat: float_bottom = max(float_bottom or 0, R.y1)
                if not gfloat: flush()
                gap = None if prev_y1 is None else round(R.y0 - prev_y1, 1)
                blocks.append({'type': 'gtable', 'float': gfloat, 'page': pn + 1, 'col': col, 'y0': round(R.y0, 1), 'x0': round(R.x0 - colL, 1), 'xs': [round(x, 1) for x in xs],
                               'ys': [round(y, 1) for y in ys], 'cells': cells, 'gap': gap, 'col_start': first_in_col, 'box': None, 'runs': [], 'text': '[표]'})
                if not gfloat: first_in_col = False; prev_y1 = R.y1
                continue
            if kind_i == 'tbl':
                flush(); (tcol, rules), tl = it
                cap = [l for l in tl if l['y0'] < rules[0] - 2]
                body = [l for l in tl if l['y0'] >= rules[0] - 2]
                # 행: y 병합
                rws = []
                for l in sorted(body, key=lambda l: (l['y0'], l['x0'])):
                    if rws and abs(rws[-1][0] - l['y0']) < 8: rws[-1][1].append(l)
                    else: rws.append([l['y0'], [l]])
                hdr = [r for r in rws if r[0] < rules[1]]; dat = [r for r in rws if r[0] >= rules[1]]
                ncol = max(len(r[1]) for r in dat)
                cols = sorted([l['x0'] for l in dat[0][1]]) if dat else []
                tx0 = min(l['x0'] for l in tl); tx1 = max(l['x1'] for l in tl)
                def colof(x): return min(range(len(cols)), key=lambda i: abs(cols[i] - x))
                def celltext(rl):
                    t = [''] * len(cols)
                    for l in rl: j = colof(l['x0']); t[j] = (t[j] + ' ' + txt(l['runs'])).strip()
                    return t
                header = [''] * len(cols)
                for r in hdr:
                    for l in r[1]:
                        if cap and l in cap: continue
                        j = colof((l['x0'] + l['x1']) / 2 - (l['x1'] - l['x0']) / 2)
                        header[j] = (header[j] + ' ' + txt(l['runs'])).strip()
                capt = ' '.join(txt(l['runs']) for l in cap)
                if cap: header = [h for h in header]
                drows = [celltext(r[1]) for r in dat]
                # 열 경계: 인접 열 사이 중앙(데이터 셀 기준)
                ext = [[min(l['x0'] for r in dat for l in r[1] if colof(l['x0']) == j), max(l['x1'] for r in dat for l in r[1] if colof(l['x0']) == j)] for j in range(len(cols))]
                hext = [[l['x0'], l['x1']] for r in hdr for l in r[1]]
                bounds = [tx0 - 1] + [round((ext[j][1] + ext[j + 1][0]) / 2, 1) for j in range(len(cols) - 1)] + [tx1 + 1]
                gap = None if prev_y1 is None else round(rules[0] - 22 - prev_y1, 1)
                blocks.append({'type': 'table', 'page': pn + 1, 'col': col, 'y0': round(rules[0], 1), 'caption': capt, 'header': header, 'rows': drows,
                               'bounds': bounds, 'rules': rules, 'gap': gap, 'col_start': first_in_col, 'box': None, 'runs': [], 'text': '[표] ' + capt})
                first_in_col = False; prev_y1 = rules[-1]; continue
            ln = it
            segs_t = ln['segs']
            runs = []
            for k, sg in enumerate(segs_t):
                if k: runs.append({'t': '\t', 'f': 'sin', 's': 11.2, 'ul': False, 'box': False, 'b': False, 'i': False})
                runs.extend(sg['runs'])
            t = txt(segs_t[0]['runs']); fr = segs_t[0]['runs'][0]; rel = ln['x0'] - colL
            tabs = [round(sg['x0'] - ln['x0'], 1) for sg in segs_t[1:]]
            kind = None; new = True; _lab = False
            _eqonly = A.math and any(r['f'] == 'eq' for sg in segs_t for r in sg['runs']) and all(r['f'] == 'eq' or not any(ch.isalnum() for ch in r['t']) for sg in segs_t for r in sg['runs'])
            _tb = next((b for b in tagboxes if b[0] - 3 <= ln['x0'] <= b[2] and b[1] - 6 <= ln['y0'] <= b[3]), None)
            if _tb: kind = 'tagbox'; ln['_tw'] = round(_tb[2] - _tb[0], 1)
            elif _eqonly and rel > 20 and t[:1] not in CIRC and zone != 'bogi': kind = 'dispeq'
            elif re.match(r'^\[\d+～\d+\]', t): kind = 'instr'; zone = 'passage'
            elif re.match(r'^\d+\.', t) and fr['f'] == 'gyeon' and fr['s'] > 12: kind = 'stem'; zone = 'stem'
            elif t[:1] in CIRC: kind = 'choice_row' if len(segs_t) > 1 else 'choice'; zone = 'choice'
            elif re.match(r'^<보\s*기>$', t): kind = 'bogi_title'; zone = 'bogi'
            elif A.lang == 'soc' and re.match(r'^[ㄱ-ㅎ]\.', t) and zone in ('bogi', 'choice', 'stem', 'qbox'): kind = 'bogi_item'; zone = 'bogi'
            elif zone == 'passage' and re.match(r'^\([가-힣]\)$', t): kind = 'label'
            elif t[:1] == '◦' and not (A.lang == 'soc' and box_of(ln['y0'], ln['x0']) is not None and zone != 'bogi'): kind = 'bogi_item'
            elif t[:1] == '*' and fr['s'] <= 11.1: kind = 'footnote'
            elif 'Å±×·¡ÇÈ' in (fr.get('f') or '') or (fr['s'] == 11.4 and fr['f'] == 'sin' and zone is None) or False: kind = 'notice'
            elif re.match(r'^[A-Za-z]+:$', t) and zone in ('stem', 'choice'): kind = 'dialogue'
            if kind == 'notice' and cur is not None and cur['type'] == 'notice' and not first_in_col: kind = None; new = False; _cont_notice = True
            else: _cont_notice = False
            bid = box_of(ln['y0'], ln['x0']) if A.lang == 'soc' else None
            if kind is None and bid is not None and zone in ('stem', 'qbox', 'choice') :
                label = re.match(r'^(\([가-힣]\)|[갑을병정]:|[○◦]|[ㄱ-ㅎ]\.)', t) is not None
                if cur is not None and cur['type'] == 'qbox' and cur.get('boxid') == (pn, bid) and not label and (ln['x0'] <= prev_x0 + 5 or (cur.get('lab') and len(cur.get('_xs', [])) == 1)):
                    kind = None; new = False; _cont_notice = True
                else:
                    kind = 'qbox'; zone = 'qbox'; _lab = label
            if kind is None and float_bottom is not None and cur is not None and ln['y0'] >= float_bottom - 3 and cur['type'] in ('stem', 'stemcont', 'passage', 'bogi', 'bogi_item'):
                kind = 'stemcont' if cur['type'] in ('stem', 'stemcont') else cur['type']; new = True; float_bottom = None
            if kind is None:
                # 이어지는 줄 / 새 문단 판정
                if _cont_notice: new = False
                elif cur is None: kind = {'passage': 'passage', 'bogi': 'bogi'}.get(zone, 'passage'); new = True
                elif cur['type'] == 'dispeq':
                    kind = 'stemcont'; new = True
                elif cur['type'] in ('choice', 'stem', 'bogi_item', 'notice', 'stemcont') and ln['x0'] > cur['x0'] - 1 and not (fr['f'] == 'times' and cur['type'] in ('stem', 'choice')):
                    new = False
                elif cur['type'] in ('stem', 'choice') and fr['f'] == 'times':
                    kind = 'passage'; new = True
                elif cur['type'] in ('passage', 'bogi', 'label'):
                    if cur['type'] == 'label': new = True; kind = 'passage'
                    elif ln['x0'] > prev_x0 + 5: new = True; kind = cur['type']
                    else: new = False
                else: kind = 'bogi' if zone == 'bogi' else 'passage'; new = True
            if kind == 'dialogue':
                # 오른쪽으로 이어지는 긴 선 길이
                ln_r = max([s[1] for s in segs if ln['y1'] - 3 <= s[2] <= ln['y1'] + 10 and s[0] >= ln['x0'] - 3 and (s[1] - s[0]) > 100] or [ln['x1']])
                cur_line_len = round(ln_r - ln['x1'], 1)
            # 단 처음 줄이 들여쓰기 없이 이어지면 앞 단 문단의 연속
            if first_in_col and kind in (None,) and cur is not None: new = False
            if first_in_col and cur is not None and kind in ('passage', 'bogi') and rel < 14 and cur['type'] == kind and ln['x0'] <= (min(body_x) if body_x else colL + 8) + 5:
                cur['runs'].append(sp_run()); cur['runs'].extend(runs); cur['spans_cols'] = True; cur.setdefault('_ys', []).append((ln['y0'], ln['y1']))
                first_in_col = False; prev_y1 = ln['y1']; prev_x0 = ln['x0']; continue
            if new:
                flush()
                gap = None if prev_y1 is None else round(ln['y0'] - prev_y1, 1)
                bx = None
                if kind in ('passage', 'label') and A.lang == 'ko': bx = 'passage'
                if kind in ('bogi', 'bogi_title', 'bogi_item'): bx = 'bogi'
                if kind == 'notice' or in_textbox(ln['y0'], ln['x0']): bx = 'notice'
                if kind == 'qbox': bx = 'passage'
                cur = {'type': kind, 'page': pn + 1, 'col': col, 'y0': round(ln['y0'], 1), 'runs': list(runs), 'box': bx, 'gap': gap,
                       'col_start': first_in_col, 'x0': round(ln['x0'], 1)}
                if tabs: cur['tabs'] = tabs
                if kind == 'qbox': cur['boxid'] = (pn, bid); cur['lab'] = _lab
                cur['_xs'] = [ln['x0']]; cur['_ys'] = [(ln['y0'], ln['y1'])]; cur['_adv'] = [ln['adv']] if ln['adv'] else []; cur['_tr'] = [ln['tr']] if ln['tr'] else []
                if kind == 'dialogue': cur['line_len'] = cur_line_len
                if kind == 'tagbox': cur['w'] = ln['_tw']
                if kind in ('footnote',): cur['align'] = 'RIGHT'
                first_in_col = False
            else:
                cur['runs'].append(sp_run()); cur['runs'].extend(runs); cur.setdefault('_ys', []).append((ln['y0'], ln['y1']))
                cur.setdefault('_xs', []).append(ln['x0'])
                if ln['adv']: cur.setdefault('_adv', []).append(ln['adv'])
                if ln['tr']: cur.setdefault('_tr', []).append(ln['tr'])
            prev_y1 = ln['y1']; prev_x0 = ln['x0']
        flush()

for b in blocks:
    if not b['runs']: continue
    if b['type'] not in ('choice_row', 'footnote'):
        if 'tabs' in b: b['runs_tab'] = [dict(r) for r in b['runs']]
        for r in b['runs']:
            if r['t'] == '	': r['t'] = ' '
    m = []
    for r in b['runs']:
        if m and 'eq' not in r and 'eq' not in m[-1] and all(m[-1][k] == r[k] for k in ('f', 's', 'ul', 'box', 'b', 'i')): m[-1]['t'] += r['t']
        else: m.append(dict(r))
    b['runs'] = m; b['text'] = txt(m)
    if b['type'] == 'label': b['box'] = 'passage' if A.lang == 'ko' else None
json.dump(blocks, open(A.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(len(blocks), 'blocks', dict(Counter(b['type'] for b in blocks)))
for b in blocks:
    fl = ''.join(c for c, k in (('U', any(r.get('ul') for r in b['runs'])), ('B', any(r.get('box') for r in b['runs'])), ('I', any(r.get('i') for r in b['runs']))) if k)
    print(f"p{b['page']}c{b['col']} {b['type']:10s} box={str(b['box']):7s} gap={b['gap']} {'CS ' if b['col_start'] else ''}{fl} | {b['text'][:48]}")
