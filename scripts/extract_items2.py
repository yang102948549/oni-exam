"""PDF 시험지 → 문항 블록 JSON (국어·영어 공통).
usage: python -X utf8 scripts/extract_items2.py PDF FIRST LAST OUT.json [--lang ko|en] [--figdir DIR]
블록 type: instr label passage stem choice choice_row footnote notice dialogue bogi_title bogi bogi_item figure table
"""
import argparse, json, re
from pathlib import Path
import pymupdf

ap = argparse.ArgumentParser()
ap.add_argument('pdf'); ap.add_argument('first', type=int); ap.add_argument('last', type=int); ap.add_argument('out')
ap.add_argument('--lang', default='ko'); ap.add_argument('--figdir', default='work/figs')
A = ap.parse_args()
MID, CIRC = 421.0, '①②③④⑤'
Path(A.figdir).mkdir(parents=True, exist_ok=True)

def fclass(name):
    n = name or ''
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
    return [{'t': t, 'f': k[0], 's': k[1], 'ul': k[2], 'box': k[3], 'b': k[4], 'i': k[5]} for k, t in runs]

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
    top = 225 if pn == 0 else 150
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
    figs = []; textbox_regions = []
    for f in merged:
        nlines = sum(1 for b in raw['blocks'] if b['type'] == 0 for l in b['lines'] if f[2] - 2 <= l['bbox'][1] and l['bbox'][3] <= f[4] + 2 and f[1] - 3 <= l['bbox'][0] <= f[3] and ''.join(c['c'] for sp in l['spans'] for c in sp['chars']).strip())
        if nlines >= 3: textbox_regions.append(tuple(f[1:5]))
        else: figs.append(f)
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
        # 같은 y 줄 병합(선택지 가로 배치, 각주)
        rows = []
        for l in sorted(L, key=lambda l: (l['y0'], l['x0'])):
            if rows and abs(rows[-1]['y0'] - l['y0']) < 3.0 and l['x0'] > rows[-1]['x1'] - 1:
                r = rows[-1]
                if l['x0'] - r['x1'] < 12:
                    last = r['segs'][-1]; last['runs'] = last['runs'] + [sp_run()] + l['runs']; last['x1'] = l['x1']
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
        def ykey(it):
            if it[0] == 'line': return it[1]['y0']
            if it[0] == 'fig': return it[1][2]
            return it[1][0][1][0] - 24
        items.sort(key=ykey)
        first_in_col = True; prev_y1 = None; prev_x0 = 0
        # 기준 x(문단 첫줄 들여쓰기 판정): 같은 단의 본문 줄 중 최소 x0
        body_x = [r['x0'] for k, r in items if k == 'line' and not re.match(r'^(\[\d|\d+\.\s|[①-⑤]|\*|<보)', txt(r['segs'][0]['runs'])) and (r['x1'] - r['x0']) > 150]
        for kind_i, it in items:
            if kind_i == 'fig':
                flush(); f = it
                png = Path(A.figdir) / f'fig_p{pn + 1}_{f[5]}.png'
                page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(f[1], f[2], f[3], f[4])).save(png)
                gap = None if prev_y1 is None else round(f[2] - prev_y1, 1)
                blocks.append({'type': 'figure', 'page': pn + 1, 'col': col, 'y0': round(f[2], 1), 'w': round(f[3] - f[1], 1), 'h': round(f[4] - f[2], 1),
                               'x0': round(f[1] - colL, 1), 'png': str(png).replace('\\', '/'), 'gap': gap, 'col_start': first_in_col, 'box': None, 'runs': [], 'text': '[그림]'})
                first_in_col = False; prev_y1 = f[4]; continue
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
            kind = None; new = True
            if re.match(r'^\[\d+～\d+\]', t): kind = 'instr'; zone = 'passage'
            elif re.match(r'^\d+\.\s', t) and fr['f'] == 'gyeon' and fr['s'] > 12: kind = 'stem'; zone = 'stem'
            elif t[:1] in CIRC: kind = 'choice_row' if len(segs_t) > 1 else 'choice'; zone = 'choice'
            elif re.match(r'^<보\s*기>$', t): kind = 'bogi_title'; zone = 'bogi'
            elif zone == 'passage' and re.match(r'^\([가-힣]\)$', t): kind = 'label'
            elif t[:1] == '◦': kind = 'bogi_item'
            elif t[:1] == '*' and fr['s'] <= 11.1: kind = 'footnote'
            elif 'Å±×·¡ÇÈ' in (fr.get('f') or '') or (fr['s'] == 11.4 and fr['f'] == 'sin' and zone is None) or False: kind = 'notice'
            elif re.match(r'^[A-Za-z]+:$', t) and zone in ('stem', 'choice'): kind = 'dialogue'
            if kind == 'notice' and cur is not None and cur['type'] == 'notice' and not first_in_col: kind = None; new = False; _cont_notice = True
            else: _cont_notice = False
            if kind is None:
                # 이어지는 줄 / 새 문단 판정
                if _cont_notice: new = False
                elif cur is None: kind = {'passage': 'passage', 'bogi': 'bogi'}.get(zone, 'passage'); new = True
                elif cur['type'] in ('choice', 'stem', 'bogi_item', 'notice') and ln['x0'] > cur['x0'] - 1 and not (fr['f'] == 'times' and cur['type'] in ('stem', 'choice')):
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
                cur = {'type': kind, 'page': pn + 1, 'col': col, 'y0': round(ln['y0'], 1), 'runs': list(runs), 'box': bx, 'gap': gap,
                       'col_start': first_in_col, 'x0': round(ln['x0'], 1)}
                if tabs: cur['tabs'] = tabs
                cur['_ys'] = [(ln['y0'], ln['y1'])]; cur['_adv'] = [ln['adv']] if ln['adv'] else []; cur['_tr'] = [ln['tr']] if ln['tr'] else []
                if kind == 'dialogue': cur['line_len'] = cur_line_len
                if kind in ('footnote',): cur['align'] = 'RIGHT'
                first_in_col = False
            else:
                cur['runs'].append(sp_run()); cur['runs'].extend(runs); cur.setdefault('_ys', []).append((ln['y0'], ln['y1']))
                if ln['adv']: cur.setdefault('_adv', []).append(ln['adv'])
                if ln['tr']: cur.setdefault('_tr', []).append(ln['tr'])
            prev_y1 = ln['y1']; prev_x0 = ln['x0']
        flush()

for b in blocks:
    if not b['runs']: continue
    m = []
    for r in b['runs']:
        if m and all(m[-1][k] == r[k] for k in ('f', 's', 'ul', 'box', 'b', 'i')): m[-1]['t'] += r['t']
        else: m.append(dict(r))
    b['runs'] = m; b['text'] = txt(m)
    if b['type'] == 'label': b['box'] = 'passage' if A.lang == 'ko' else None
json.dump(blocks, open(A.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(len(blocks), 'blocks', dict(Counter(b['type'] for b in blocks)))
for b in blocks:
    fl = ''.join(c for c, k in (('U', any(r.get('ul') for r in b['runs'])), ('B', any(r.get('box') for r in b['runs'])), ('I', any(r.get('i') for r in b['runs']))) if k)
    print(f"p{b['page']}c{b['col']} {b['type']:10s} box={str(b['box']):7s} gap={b['gap']} {'CS ' if b['col_start'] else ''}{fl} | {b['text'][:48]}")
