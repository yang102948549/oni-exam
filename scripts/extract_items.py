"""PDF 시험지 쪽 → 문항 구조(JSON) 추출. 줄이 아니라 블록(발문/지문/선택지/보기)과 인라인 서식(밑줄·글자 테두리)을 얻는다.
usage: python -X utf8 scripts/extract_items.py 국어.pdf 1 3 out.json
블록 type: instr | label | passage | stem | choice | bogi_title | bogi | bogi_item
box: 'passage' | 'bogi' | None    (문단 테두리로 복원할 상자)
"""
import json, re, sys
import pymupdf

PDF, P0, P1, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
MID = 421.0
CIRC = '①②③④⑤'

def font_class(name):
    n = name or ''
    if '°ß°íµñ' in n: return 'gyeongo'      # 견고딕
    if '°ß¸íÁ¶' in n: return 'gyeon'         # 견명조
    if '°íµñ' in n or 'Gulim' in n or '³ª·ç' in n: return 'jung'  # 중/태고딕 계열
    return 'sin'                              # 신명조 계열

def hsegs(page):
    """짧은 수평선(밑줄·글자 테두리 윗/아랫변) 수집"""
    segs = []
    for d in page.get_drawings():
        for it in d['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.2 and abs(a.x - b.x) > 3:
                    segs.append((min(a.x, b.x), max(a.x, b.x), a.y, d.get('width') or 0))
    return segs

def marks_for_line(line, segs):
    """줄 bbox 기준 밑줄 구간·글자 테두리 구간 [(x0,x1)]"""
    x0, y0, x1, y1 = line['bbox']
    ul, box = [], []
    for sx0, sx1, sy, w in segs:
        if sx1 < x0 - 1 or sx0 > x1 + 1 or sx1 - sx0 > 300: continue
        if 0.44 <= w <= 0.6 and y1 - 4 <= sy <= y1 + 3: ul.append((sx0, sx1))   # 밑줄(0.54pt)
    tops = [s for s in segs if abs(s[3] - 0.36) < 0.05 and y0 - 4 <= s[2] <= y0 + 3 and s[1] - s[0] < 130 and x0 - 4 <= s[0] and s[1] <= x1 + 6]
    bots = [s for s in segs if abs(s[3] - 0.36) < 0.05 and y1 - 3 <= s[2] <= y1 + 4 and s[1] - s[0] < 130]
    for t in tops:
        for b in bots:
            if abs(t[0] - b[0]) < 0.5 and abs(t[1] - b[1]) < 0.5 and 8 < b[2] - t[2] < 20:
                box.append((t[0], t[1]))
    return ul, list({(round(a, 1), round(b, 1)) for a, b in box})

def line_runs(rawline, ul, box):
    runs = []
    for sp in rawline['spans']:
        fc, sz = font_class(sp['font']), round(sp['size'], 1)
        for ch in sp['chars']:
            cx = (ch['bbox'][0] + ch['bbox'][2]) / 2
            u = any(a - 0.5 <= cx <= b + 0.5 for a, b in ul)
            bx = any(a - 0.5 <= cx <= b + 0.5 for a, b in box)
            key = (fc, sz, u, bx)
            if runs and runs[-1]['k'] == key: runs[-1]['t'] += ch['c']
            else: runs.append({'k': key, 't': ch['c']})
    return [{'t': r['t'], 'f': r['k'][0], 's': r['k'][1], 'ul': r['k'][2], 'box': r['k'][3]} for r in runs]

def strip_runs(runs):
    while runs and not runs[-1]['t'].strip(): runs.pop()
    if runs: runs[-1]['t'] = runs[-1]['t'].rstrip()
    while runs and not runs[0]['t'].strip(): runs.pop(0)
    if runs: runs[0]['t'] = runs[0]['t'].lstrip()
    return runs

def text_of(runs): return ''.join(r['t'] for r in runs)

doc = pymupdf.open(PDF)
blocks = []
cur = None; zone = None; prev_col_end = None
for pn in range(P0 - 1, P1):
    page = doc[pn]; segs = hsegs(page)
    top = 225 if pn == 0 else 150
    for col in (0, 1):
        lines = []
        raw = page.get_text('rawdict')
        for b in raw['blocks']:
            if b['type']: continue
            for l in b['lines']:
                x0, y0, x1, y1 = l['bbox']
                if not (top < y0 < 1075): continue
                if (x0 >= MID) != bool(col): continue
                runs = strip_runs(line_runs(l, *marks_for_line(l, segs)))
                if runs: lines.append({'x0': x0, 'y0': y0, 'y1': y1, 'runs': runs})
        lines.sort(key=lambda l: l['y0'])
        colL = 88.0 if col == 0 else 437.0
        first_in_col = True; prev_y1 = None
        def flush():
            global cur
            if cur: blocks.append(cur); cur = None
        for ln in lines:
            t = text_of(ln['runs']); rel = ln['x0'] - colL
            kind = None
            if re.match(r'^\[\d+～\d+\]', t): kind = 'instr'; zone = 'passage'
            elif re.match(r'^\d+\.\s', t) and ln['runs'][0]['f'] == 'gyeon' or (re.match(r'^\d+\.', t) and ln['runs'][0]['s'] > 12 and ln['runs'][0]['f'] == 'gyeon'):
                kind = 'stem'; zone = 'stem'
            elif t[:1] in CIRC and zone in ('stem', 'choice', 'bogi'): kind = 'choice'; zone = 'choice'
            elif re.match(r'^<보\s*기>$', t): kind = 'bogi_title'; zone = 'bogi'
            elif zone == 'passage' and re.match(r'^\([가-힣]\)$', t): kind = 'label'
            elif zone == 'bogi' and t[:1] == '◦': kind = 'bogi_item'
            elif zone == 'passage' and rel > 14 and not (cur and cur['type'] == 'label' and False): kind = 'passage'
            elif zone == 'bogi' and rel > 24 and cur and cur['type'] in ('bogi_title', 'bogi'): kind = 'bogi'
            # 이어지는 줄(내어쓰기) / 단·쪽을 넘어 이어지는 문단
            if kind is None and first_in_col and cur is not None and cur['type'] in ('passage', 'bogi', 'choice', 'bogi_item', 'stem') and rel < 14:
                kind = '_cont'
            if kind == '_cont':
                cur['runs'].append({'t': ' ', 'f': 'sin', 's': 11.2, 'ul': False, 'box': False}); cur['runs'].extend(ln['runs'])
                cur['spans_cols'] = True; first_in_col = False; prev_y1 = ln['y1']; continue
            if kind is None:
                if cur is None:
                    kind = {'passage': 'passage', 'bogi': 'bogi', 'stem': 'stem', 'choice': 'choice'}.get(zone, 'passage')
                    new = True
                else:
                    new = False
            else:
                new = True
            if kind in ('passage',) and cur and cur['type'] == 'passage' and kind and not new: new = False
            if new:
                flush()
                gap = None if prev_y1 is None else round(ln['y0'] - prev_y1, 1)
                cur = {'type': kind, 'page': pn + 1, 'col': col, 'y0': round(ln['y0'], 1), 'runs': list(ln['runs']),
                       'box': {'passage': 'passage', 'label': None}.get(kind) if zone == 'passage' and kind in ('passage',) else
                              ('bogi' if kind in ('bogi_title', 'bogi', 'bogi_item') else None),
                       'gap': gap, 'col_start': first_in_col, 'x0': round(ln['x0'], 1)}
                if kind == 'passage' and zone == 'passage': cur['box'] = 'passage'
                first_in_col = False
            else:
                cur['runs'].append({'t': ' ', 'f': 'sin', 's': 11.2, 'ul': False, 'box': False})
                cur['runs'].extend(ln['runs'])
            prev_y1 = ln['y1']
        flush()

# 후처리: 같은 서식의 인접 run 병합, 지문 앞 라벨은 box 유지
for b in blocks:
    m = []
    for r in b['runs']:
        if m and all(m[-1][k] == r[k] for k in ('f', 's', 'ul', 'box')): m[-1]['t'] += r['t']
        else: m.append(dict(r))
    b['runs'] = m
    b['text'] = text_of(m)
    if b['type'] == 'label': b['box'] = 'passage'
json.dump(blocks, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(len(blocks), 'blocks', dict(Counter(b['type'] for b in blocks)))
for b in blocks:
    flags = ''.join(c for c, k in (('U', any(r['ul'] for r in b['runs'])), ('B', any(r['box'] for r in b['runs']))) if k)
    print(f"p{b['page']}c{b['col']} {b['type']:10s} box={str(b['box']):8s} gap={b['gap']} {'CS ' if b['col_start'] else ''}{flags} | {b['text'][:44]}")
