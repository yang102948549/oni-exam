"""HyhwpEQ(한컴 수식 글꼴) 글리프 배치 → 한컴 수식 스크립트.
PDF의 수식은 전용 영역(PUA) 코드로 들어 있고 분수 막대·루트 가로선도 글리프다. 위치·크기로 구조를 복원한다.
"""
import statistics as st

UP = {chr(0xE000 + i): chr(65 + i) for i in range(26)}            # 이탤릭 대문자 A..Z
LOW = {chr(0xE0E5 + i): chr(97 + i) for i in range(26)}           # 이탤릭 소문자 a..z
DIG = {chr(0xE034 + i): str(i + 1) for i in range(9)}             # 1..9
DIG[chr(0xE03D)] = '0'
PUA = {'': '(', '': ')', '': '-', '': '=', '': '+', '': 'lbrace', '': 'rbrace',
       '': ':', '': ',', '': '.', '': '<', '': '>', '': 'INT', '': 'RAD',
       '': 'SUM', '': 'BAR', '': 'VEC', '': 'theta', '': 'pi', '': '|',
       '': 'BIG', '': 'BIG', '': 'BIG', '': 'BIG'}
UNI = {'×': 'times', '→': '->', '∞': 'inf', '∠': 'angle', '∪': 'cup', '≠': '!=', '≤': '<=', '≥': '>=', '⋅': 'cdot',
       '∩': 'cap', '±': 'pm', '÷': 'div', '△': 'triangle', '°': '`DEG`', '′': "'"}
WORDS = {'lim': 'lim', 'log': 'log', 'sin': 'sin', 'cos': 'cos', 'tan': 'tan', 'ln': 'ln', 'sec': 'sec', 'csc': 'csc', 'cot': 'cot'}


class G:
    __slots__ = ('tok', 'x0', 'x1', 'ox', 'oy', 's', 'y0', 'y1', 'raw')

    def __init__(self, ch, bbox, origin, size):
        self.raw = ch
        self.tok = UP.get(ch) or LOW.get(ch) or DIG.get(ch) or PUA.get(ch) or UNI.get(ch) or ch
        self.x0, self.y0, self.x1, self.y1 = bbox
        self.ox, self.oy = origin
        self.s = size
        if self.tok == 'BAR':   # 막대 글리프의 em 상자는 매우 크므로 군집·판정에는 얇은 선으로 본다
            self.y0, self.y1 = origin[1] - 0.6 * 11 - 0.8, origin[1] - 0.6 * 11 + 0.8

    @property
    def cx(self): return (self.x0 + self.x1) / 2

    @property
    def cy(self): return self.oy - 0.33 * self.s       # 수학 중심 근사


class Node:
    """분수·루트·제곱근 등 이미 해석된 부분식"""
    def __init__(self, script, x0, x1, cy, s, oy):
        self.script, self.x0, self.x1, self.cy, self.s, self.oy = script, x0, x1, cy, s, oy
        self.tok = 'NODE'

    @property
    def cx(self): return (self.x0 + self.x1) / 2


def cluster(glyphs, other_boxes):
    """수식 글리프를 가까운 것끼리 묶는다. 한글 본문 글리프(other_boxes)가 사이에 있으면 끊는다."""
    n = len(glyphs); parent = list(range(n))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def blocked(a, b):
        lo, hi = min(a.x1, b.x1), max(a.x0, b.x0)
        if lo >= hi: return False
        ylo, yhi = min(a.y0, b.y0), max(a.y1, b.y1)
        return any(ob[0] < hi and ob[2] > lo and ob[1] < yhi and ob[3] > ylo for ob in other_boxes)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = glyphs[i], glyphs[j]
            gap = max(a.x0, b.x0) - min(a.x1, b.x1)
            vgap = max(a.y0, b.y0) - min(a.y1, b.y1)
            if gap > 5.0 or vgap > 4.0 or abs(a.oy - b.oy) > 22: continue
            if abs(a.oy - b.oy) > 4.5:   # 위아래로 쌓인 관계는 막대·연산자·첨자일 때만 같은 수식으로 본다
                ops = {a.tok, b.tok} & {'BAR', 'SUM', 'INT', 'RAD', 'BIG', 'VEC'}
                script_rel = min(a.s, b.s) < 0.86 * max(a.s, b.s) and abs(a.oy - b.oy) <= 0.95 * max(a.s, b.s)
                if not ops and not script_rel: continue
            if blocked(a, b): continue
            parent[find(i)] = find(j)
    groups = {}
    for i in range(n): groups.setdefault(find(i), []).append(glyphs[i])
    gl = list(groups.values())
    # 큰 중괄호가 있으면 그 높이 안에서 오른쪽으로 이어지는 식 덩어리를 같은 수식으로 합친다
    for c in gl[:]:
        big = [g for g in c if g.tok == 'BIG']
        if not big or c not in gl: continue
        by0, by1 = min(g.y0 for g in big), max(g.y1 for g in big); bx1 = max(g.x1 for g in big)
        changed = True
        while changed:
            changed = False
            for o in gl[:]:
                if o is c: continue
                oy0, oy1 = min(g.y0 for g in o), max(g.y1 for g in o); ox0 = min(g.x0 for g in o)
                cx1 = max(g.x1 for g in c)
                if ox0 >= bx1 - 1 and oy1 > by0 - 4 and oy0 < by1 + 4 and ox0 - cx1 < 70:
                    ok = not any(ob[0] < ox0 and ob[2] > cx1 and ob[1] < by1 and ob[3] > by0 for ob in other_boxes)
                    if ok: c.extend(o); gl.remove(o); changed = True
    return gl


def base_size(gs):
    sizes = [g.s for g in gs if g.tok not in ('BAR', 'RAD', 'SUM', 'INT', 'BIG', ' ', '(', ')', 'lbrace', 'rbrace', '|', 'VEC')]
    if not sizes: return 11.0
    big = [round(x, 1) for x in sizes if x >= 9.0] or [round(x, 1) for x in sizes]
    return max(set(big), key=lambda v: (big.count(v), -v))


def _join(parts): return ' '.join(p for p in parts if p)


def parse(gs, S=None):
    """글리프 목록 → 스크립트 문자열"""
    gs = [g for g in gs if g.tok != ' ']
    if not gs: return ''
    S = S or base_size(gs)
    items = list(gs)
    # --- 큰 중괄호(연립/조각) ---
    big = [g for g in items if g.tok == 'BIG']
    if big:
        return _cases(items, big, S)
    # --- 루트: RAD 글리프 + 그 오른쪽의 BAR ---
    rads = sorted([g for g in items if g.tok == 'RAD'], key=lambda g: g.x0)
    for r in rads:
        bars = [b for b in items if b.tok == 'BAR' and abs(b.x0 - r.x1) < 3.0]
        if not bars: continue
        b = bars[0]; sz = _level(items, b)
        axis = b.oy - 0.6 * sz
        inner = [g for g in items if g is not b and g is not r and b.x0 - 0.5 <= g.cx <= b.x1 + 0.5 and axis - 0.5 < g.cy < axis + 1.5 * sz
                 and not (getattr(g, 'tok', '') == 'BAR' and g.x0 < b.x0 - 1.0)]
        if not inner: continue
        sc = parse(inner, S=sz)
        used = set(map(id, inner)) | {id(b), id(r)}
        node = Node('sqrt {%s}' % sc, r.x0, b.x1, (axis + max(g.oy for g in inner)) / 2 - 0.1 * S, sz, max(g.oy for g in inner))
        items = [g for g in items if id(g) not in used] + [node]
    # --- 윗줄(선분 표기)·분수: 남은 BAR ---
    while True:
        bars = [g for g in items if getattr(g, 'tok', '') == 'BAR']
        if not bars: break
        # 먼저 '위에 아무것도 없고 바로 아래에 글자가 있는' 막대(윗줄)를 처리한다
        pick = None; kind = 'frac'
        for cand in bars:
            szc = _level([g for g in items if g is not cand], cand); axc = cand.oy - 0.6 * szc
            inx = [g for g in items if g is not cand and cand.x0 - 1.0 <= g.cx <= cand.x1 + 1.0]
            above = [g for g in inx if axc - 1.4 * szc < g.cy < axc]
            below = [g for g in inx if axc < g.cy < axc + 1.3 * szc]
            if below and not above: pick, kind = cand, 'over'; break
        b = pick or bars[0]
        sz = _level([g for g in items if g is not b], b)
        axis = b.oy - 0.6 * sz
        if kind == 'over':
            members = [g for g in items if g is not b and b.x0 - 1.0 <= g.cx <= b.x1 + 1.0 and axis < g.cy < axis + 1.3 * sz]
            used = set(map(id, members)) | {id(b)}
            node = Node('bar {%s}' % parse(members, S=sz), b.x0, b.x1, axis + 0.5 * sz, sz, max(g.oy for g in members))
            items = [g for g in items if id(g) not in used] + [node]
            continue
        members = [g for g in items if g is not b and b.x0 - 1.0 <= g.cx <= b.x1 + 1.0 and abs(_cy(g) - axis) < 3.2 * sz]
        num = [g for g in members if _cy(g) < axis]; den = [g for g in members if _cy(g) >= axis]
        used = set(map(id, members)) | {id(b)}
        if not num and not den:
            items = [g for g in items if g is not b]; continue
        ns, ds = parse(num, S=sz), parse(den, S=sz)
        node = Node('{%s} over {%s}' % (ns, ds), b.x0, b.x1, axis, sz, axis + 0.33 * sz)
        items = [g for g in items if id(g) not in used] + [node]
    # --- 큰 연산자(Σ, ∫, lim)와 첨자 ---
    items.sort(key=lambda g: (g.x0 + g.x1) / 2 if getattr(g, 'tok', '') == 'NODE' else g.x0)
    items = _words(items, S)
    items, limits = _claim_limits(items, S)
    return _sequence(items, S, limits)


def _cy(g): return g.cy if not isinstance(g, Node) else g.cy


def _level(others, bar):
    c = [g.s for g in others if isinstance(g, G) and bar.x0 - 1 <= g.cx <= bar.x1 + 1 and abs(g.oy - bar.oy) < 25 and g.tok not in ('BAR', 'RAD')]
    if not c: return 11.0
    return st.mode([round(x, 1) for x in c]) if len(set(round(x, 1) for x in c)) == 1 else max(set(round(x, 1) for x in c), key=lambda v: sum(1 for x in c if round(x, 1) == v))


def _claim_limits(items, S):
    """Σ·lim 위아래에 놓인 작은 글리프를 한계식으로 먼저 가져간다(연산자보다 왼쪽에서 시작해도 된다)."""
    limits = {}
    ops = [g for g in items if isinstance(g, G) and (g.tok == 'SUM' or g.tok == 'WORD:lim')]
    for op in ops:
        oc = (op.y0 + op.y1) / 2
        up, dn = [], []
        for g in items:
            if g is op or g.s >= 0.86 * S or isinstance(g, Node) and False: continue
            if op.x0 - 4 <= g.cx <= op.x1 + 4:
                (up if g.cy < oc - 0.1 * (op.y1 - op.y0) else dn).append(g)
        if op.tok == 'WORD:lim': dn = [g for g in dn if g.cy > op.cy + 0.1 * S]; up = []
        if up or dn:
            limits[id(op)] = (up, dn)
    claimed = {id(g) for u, d in limits.values() for g in u + d}
    return [g for g in items if id(g) not in claimed], limits


def _words(items, S):
    """로마체 영문 연속 글자를 단어(lim, log, sin ...)로 묶는다. 작은 첨자 글리프가 끼어 있어도 본문 글자끼리만 본다."""
    small = [g for g in items if g.s < 0.85 * S]
    main = [g for g in items if g.s >= 0.85 * S]
    out = []; i = 0
    while i < len(main):
        g = main[i]
        if isinstance(g, G) and len(g.raw) == 1 and g.raw.isascii() and g.raw.isalpha():
            j = i; w = ''
            while j < len(main) and isinstance(main[j], G) and main[j].raw.isascii() and main[j].raw.isalpha() and abs(main[j].oy - g.oy) < 1.5 and (j == i or main[j].x0 - main[j - 1].x1 < 2.5):
                w += main[j].raw; j += 1
            if w in WORDS or len(w) > 1:
                x0, x1 = g.x0, main[j - 1].x1
                n = G(w, (x0, g.y0, x1, g.y1), (x0, g.oy), g.s); n.tok = 'WORD:' + (WORDS.get(w) or w)
                out.append(n); i = j; continue
        out.append(g); i += 1
    merged = out + small
    merged.sort(key=lambda g: (g.x0 + g.x1) / 2 if isinstance(g, Node) else g.x0)
    return merged


def _tokstr(g):
    if isinstance(g, Node): return g.script
    t = g.tok
    if t.startswith('WORD:'):
        w = t[5:]
        return w if w in WORDS.values() else 'rm "%s"' % w
    if t in ('SUM',): return 'sum'
    if t in ('INT',): return 'int'
    if t == 'VEC': return ''
    if g.raw.isascii() and g.raw.isalpha() and len(g.raw) == 1: return 'rm %s' % g.raw   # 로마체 한 글자(점 이름 등)
    return t


def _sequence(items, S, limits=None):
    limits = limits or {}
    base_items = []; scripts = []   # scripts: (base_index, kind, element)
    last = None
    for it in items:
        small = it.s < 0.86 * S if not isinstance(it, Node) else it.s < 0.86 * S
        if small and last is not None:
            scripts.append((last, it))
        else:
            base_items.append(it); last = it
    # 각 기준 요소에 붙는 첨자 모으기
    info = {id(b): {'sup': [], 'sub': [], 'up': [], 'dn': []} for b in base_items}
    for b, it in scripts:
        big_op = getattr(b, 'tok', '') in ('SUM', 'WORD:lim')
        ref = b.cy if not isinstance(b, Node) else b.cy
        d = it.cy - ref
        centered = big_op and it.x0 < b.x1 - 1.5
        if centered: info[id(b)]['up' if d < 0 else 'dn'].append(it)
        else: info[id(b)]['sup' if d < -0.12 * S else 'sub'].append(it)
    parts = []
    for b in base_items:
        s = _tokstr(b)
        inf = info[id(b)]
        def sc(lst):
            lst = sorted(lst, key=lambda g: g.x0 if not isinstance(g, Node) else g.x0)
            return parse_list(lst)
        if id(b) in limits:
            up, dn = limits[id(b)]
            if dn: s += ' _{%s}' % sc(sorted(dn, key=lambda g: g.x0))
            if up: s += ' ^{%s}' % sc(sorted(up, key=lambda g: g.x0))
        elif getattr(b, 'tok', '') in ('SUM', 'WORD:lim', 'INT'):
            lo = inf['dn'] or inf['sub']; hi = inf['up'] or inf['sup']
            if lo: s += ' _{%s}' % sc(lo)
            if hi: s += ' ^{%s}' % sc(hi)
        else:
            if inf['sub']: s += '_{%s}' % sc(inf['sub'])
            if inf['sup']: s += '^{%s}' % sc(inf['sup'])
            if inf['up'] or inf['dn']:
                if inf['dn']: s += '_{%s}' % sc(inf['dn'])
                if inf['up']: s += '^{%s}' % sc(inf['up'])
        parts.append(s)
    return _join(parts)


def parse_list(lst):
    """첨자 안의 요소들(이미 노드/글리프)"""
    gl = [g for g in lst if isinstance(g, G)]
    nodes = [n for n in lst if isinstance(n, Node)]
    if not nodes and gl:
        return parse(gl, S=base_size(gl))
    items = sorted(lst, key=lambda g: g.x0)
    S = min([g.s for g in items] or [8])
    return _sequence(_words(items, S), S)


def _cases(items, big, S):
    """왼쪽 큰 중괄호 + 오른쪽 행들 → cases{ 행 # 행 } (열은 &)"""
    bx0 = min(g.x0 for g in big); bx1 = max(g.x1 for g in big)
    prefix = [g for g in items if g.tok != 'BIG' and g.x1 <= bx0 + 1.0]
    rest = [g for g in items if g.tok != 'BIG' and g not in prefix]
    rows = []
    for g in sorted(rest, key=lambda g: g.oy):
        for r in rows:
            if abs(r[0] - g.oy) < 0.9 * S: r[1].append(g); break
        else: rows.append([g.oy, [g]])
    out = []
    for oy, gs in sorted(rows, key=lambda r: r[0]):
        gs.sort(key=lambda g: g.x0)
        cols = [[gs[0]]]
        for g in gs[1:]:
            if g.x0 - max(h.x1 for h in cols[-1]) > 1.1 * S: cols.append([g])
            else: cols[-1].append(g)
        out.append(' & '.join(parse(c, S=S) for c in cols))
    pre = parse(prefix, S=S) if prefix else ''
    return (pre + ' ' if pre else '') + 'cases{ %s }' % ' # '.join(out)
