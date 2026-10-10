"""수학·과학 쪽 전처리: 수식 글리프를 수식 개체(자리표시 글자)로 바꾼 rawdict 사본, 그림 영역 목록을 만든다."""
import pymupdf
import mathparse as M

PH0 = 0xF000
EQ = {}          # 자리표시 글자 -> {'script','size','w','h','bl'}


def figure_regions(page, top=150, bottom=1075):
    """그림으로 볼 영역. 문단을 두른 단순 상자(수직선 2개뿐인 직선 틀)는 그림이 아니다."""
    rects = []
    for d in page.get_drawings():
        r = d['rect']
        if r.width > 600 or r.height > 600 or r.y0 < top or r.y1 > bottom: continue
        if r.width < 0.5 and r.height < 0.5: continue
        nonaxis = d.get('fill') is not None and d.get('fill') != (1.0, 1.0, 1.0)
        xs = set()
        for it in d['items']:
            if it[0] in ('c', 'qu'): nonaxis = True
            elif it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.x - b.x) > 0.3 and abs(a.y - b.y) > 0.3: nonaxis = True
                elif abs(a.x - b.x) <= 0.3: xs.add(round(a.x))
        rects.append([pymupdf.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1), 1, nonaxis, xs])
    merged = []
    for r, n, na, xs in rects:
        for m in merged:
            if (m[0] + pymupdf.Rect(-7, -7, 7, 7)).intersects(r):
                m[0] |= r; m[1] += n; m[2] = m[2] or na; m[3] |= xs; break
        else:
            merged.append([pymupdf.Rect(r), n, na, set(xs)])
    changed = True
    while changed:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if (merged[i][0] + pymupdf.Rect(-7, -7, 7, 7)).intersects(merged[j][0]):
                    merged[i][0] |= merged[j][0]; merged[i][1] += merged[j][1]
                    merged[i][2] = merged[i][2] or merged[j][2]; merged[i][3] |= merged[j][3]; merged.pop(j); changed = True; break
            if changed: break
    out = []
    for r, n, na, xs in merged:
        if r.width >= 70 and r.height >= 45 and n >= 5 and (na or len(xs) >= 3 + 0): out.append(r)
    return out


def _inside(b, rs):
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return any(r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1 for r in rs)


def prepare(page, fig_rects, top=150, bottom=1075, eqfont='Hyhwp', grid_rects=()):
    raw = page.get_text('rawdict')
    eqg, other, blocks, spaces, text_items, eq_items = [], [], [], [], [], []
    for b in raw['blocks']:
        if b['type']: blocks.append(b); continue
        for l in b['lines']:
            for s_ in l['spans']:
                if _inside(s_['bbox'], fig_rects): continue
                if eqfont in s_['font']:
                    for c in s_['chars']:
                        if _inside(c['bbox'], fig_rects): continue
                        if c['c'] == ' ': spaces.append((c, s_)); continue
                        eqg.append(M.G(c['c'], c['bbox'], c['origin'], s_['size']))
                else:
                    for c in s_['chars']:
                        if c['c'] in '′″':
                            eqg.append(M.G(c['c'], c['bbox'], c['origin'], s_['size'])); continue
                        text_items.append({'x0': c['bbox'][0], 'x1': c['bbox'][2], 'base': c['origin'][1], 'font': s_['font'], 'size': s_['size'], 'ch': c})
                        other.append(c['bbox'])
    eqg = [g for g in eqg if top < g.y0 and g.y1 < bottom or g.tok == 'BAR']
    clusters = M.cluster(eqg, other)
    boxes = []
    for c in clusters:
        script = M.parse(c)
        if not script.strip(): continue
        S = M.base_size(c)
        x0, x1 = min(g.x0 for g in c), max(g.x1 for g in c)
        ys0 = min((g.y0 for g in c if g.tok != 'BAR'), default=min(g.y0 for g in c))
        ys1 = max((g.y1 for g in c if g.tok != 'BAR'), default=max(g.y1 for g in c))
        rads = [g for g in c if g.tok == 'RAD']
        fbars = [g for g in c if g.tok == 'BAR' and not any(abs(g.x0 - r.x1) < 3.0 for r in rads)]
        def in_frac(g):
            for b_ in fbars:
                ax = b_.oy - 0.6 * S
                if b_.x0 - 1 <= g.cx <= b_.x1 + 1 and abs(g.cy - ax) < 3.2 * S and g is not b_: return True
            return False
        main = [g for g in c if g.s >= 0.9 * S and g.tok not in ('BAR', 'RAD', 'SUM', 'INT', 'BIG', '(', ')') and not in_frac(g)]
        if main:
            oys = sorted(round(g.oy, 1) for g in main)
            base = max(set(oys), key=lambda v: (oys.count(v), -v))
        elif fbars:
            wide = max(fbars, key=lambda g: g.x1 - g.x0)
            base = wide.oy - 0.6 * S + 0.33 * S
        else:
            base = c[0].oy
        # 높이: 막대 글리프 em 상자를 빼고 실제 글자 범위
        h = max(ys1 - ys0, S)
        ph = chr(PH0 + len(EQ))
        EQ[ph] = {'script': script, 'size': round(S, 1), 'w': round(x1 - x0, 1), 'h': round(h, 1), 'bl': round((base - ys0) / h, 3)}
        eq_items.append({'x0': x0, 'x1': x1, 'base': base, 'font': 'EQ', 'size': round(S, 1),
                         'ch': {'c': ph, 'bbox': (x0, base - 8.6, x1, base + 2.9), 'origin': (x0, base)}})
        boxes.append((x0, ys0, x1, ys1))
    # 수식 바깥의 수식 글꼴 공백은 본문 공백으로 되살린다
    for c, s_ in spaces:
        bb = c['bbox']
        if any(b[0] - 0.5 <= (bb[0] + bb[2]) / 2 <= b[2] + 0.5 and b[1] - 3 <= (bb[1] + bb[3]) / 2 <= b[3] + 3 for b in boxes): continue
        text_items.append({'x0': bb[0], 'x1': bb[2], 'base': c['origin'][1], 'font': '*½Å¸í-Áß¸íÁ¶', 'size': s_['size'], 'ch': c})
    # --- 글자·수식을 하나의 시각적 줄로 다시 묶는다(수식이 줄 한가운데 있어도 순서가 맞도록) ---
    allit = text_items + eq_items
    allit.sort(key=lambda it: it['base'])
    bands = []
    for it in allit:
        if bands and it['base'] - bands[-1][1][-1]['base'] <= 3.5: bands[-1][1].append(it)
        else: bands.append([it['base'], [it]])
    MID = 421.0
    for _, items in bands:
        for col in (0, 1):
            row = sorted([it for it in items if (it['x0'] >= MID) == bool(col)], key=lambda it: it['x0'])
            if not row: continue
            segs, cur = [], [row[0]]
            for it in row[1:]:
                gap = it['x0'] - cur[-1]['x1']
                def _in_grid(x):
                    cxx, cyy = (x['x0'] + x['x1']) / 2, x['base'] - 3
                    for gi, g in enumerate(grid_rects):
                        R = g['rect']
                        if R.x0 - 1 <= cxx <= R.x1 + 1 and R.y0 - 1 <= cyy <= R.y1 + 1:
                            xs = g['xs']; ci = next((k for k in range(len(xs) - 1) if xs[k] - 1 <= cxx < xs[k + 1] + 1), 0)
                            return (gi, ci)
                    return None
                if gap >= 12.0 or (grid_rects and _in_grid(cur[-1]) != _in_grid(it)): segs.append(cur); cur = [it]
                else:
                    if gap >= 2.2 and cur[-1]['ch']['c'] != ' ' and it['ch']['c'] != ' ':
                        sc = {'c': ' ', 'bbox': (cur[-1]['x1'], cur[-1]['ch']['bbox'][1], it['x0'], cur[-1]['ch']['bbox'][3]), 'origin': (cur[-1]['x1'], cur[-1]['base'])}
                        cur.append({'x0': cur[-1]['x1'], 'x1': it['x0'], 'base': cur[-1]['base'], 'font': '*½Å¸í-Áß¸íÁ¶', 'size': 11.2, 'ch': sc})
                    cur.append(it)
            segs.append(cur)
            for sg in segs:
                spans = []
                for it in sg:
                    key = (it['font'], round(it['size'], 1))
                    if spans and spans[-1]['_k'] == key: spans[-1]['chars'].append(it['ch'])
                    else: spans.append({'_k': key, 'font': it['font'], 'size': it['size'], 'chars': [it['ch']]})
                for sp in spans:
                    sp['bbox'] = (min(c['bbox'][0] for c in sp['chars']), min(c['bbox'][1] for c in sp['chars']),
                                  max(c['bbox'][2] for c in sp['chars']), max(c['bbox'][3] for c in sp['chars']))
                    sp.pop('_k')
                bb = (min(sp['bbox'][0] for sp in spans), min(sp['bbox'][1] for sp in spans),
                      max(sp['bbox'][2] for sp in spans), max(sp['bbox'][3] for sp in spans))
                blocks.append({'type': 0, 'bbox': bb, 'lines': [{'bbox': bb, 'spans': spans}]})
    return {'blocks': blocks}


def find_grid_tables(page, top=150, bottom=1075):
    """직선만으로 그려진 격자 표를 찾는다: 수직선 x좌표가 3개 이상, 수평선 y좌표가 2개 이상인 군집."""
    hs, vs = [], []
    for d in page.get_drawings():
        for it in d['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.3 and abs(a.x - b.x) > 3: hs.append((min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2))
                elif abs(a.x - b.x) < 0.3 and abs(a.y - b.y) > 3: vs.append(((a.x + b.x) / 2, min(a.y, b.y), max(a.y, b.y)))
    segs = [pymupdf.Rect(x0 - 0.5, y - 0.5, x1 + 0.5, y + 0.5) for x0, x1, y in hs] + [pymupdf.Rect(x - 0.5, y0 - 0.5, x + 0.5, y1 + 0.5) for x, y0, y1 in vs]
    clusters = []
    for r in segs:
        hit = [c for c in clusters if (c['rect'] + pymupdf.Rect(-2, -2, 2, 2)).intersects(r)]
        if not hit: clusters.append({'rect': pymupdf.Rect(r)}); continue
        base = hit[0]; base['rect'] |= r
        for o in hit[1:]: base['rect'] |= o['rect']; clusters.remove(o)
    out = []
    for c in clusters:
        R = c['rect']
        if R.y0 < top or R.y1 > bottom or R.width < 60 or R.height < 25 or R.width > 420: continue
        cv = [v for v in vs if R.x0 - 1 <= v[0] <= R.x1 + 1 and R.y0 - 1 <= v[1] and v[2] <= R.y1 + 1]
        ch = [h for h in hs if R.x0 - 1 <= h[0] and h[1] <= R.x1 + 1 and R.y0 - 1 <= h[2] <= R.y1 + 1]
        def merge(vals):
            vals = sorted(vals); out_ = []
            for v in vals:
                if out_ and v - out_[-1][-1] < 1.6: out_[-1].append(v)
                else: out_.append([v])
            return [sum(g) / len(g) for g in out_]
        xs = merge([v[0] for v in cv if v[2] - v[1] > 0.5 * R.height]); ys = merge([h[2] for h in ch if h[1] - h[0] > 0.5 * R.width])
        if len(xs) >= 3 and len(ys) >= 2: out.append({'rect': R, 'xs': xs, 'ys': ys})
    return out
