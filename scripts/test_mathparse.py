import sys, pymupdf
sys.path.insert(0, 'scripts')
import mathparse as M
d = pymupdf.open('test_inputs/2026학년도_수능/수학.pdf')
for pn in [int(a) - 1 for a in sys.argv[1:]]:
    p = d[pn]; eqg = []; other = []
    for b in p.get_text('rawdict')['blocks']:
        if b['type']: continue
        for l in b['lines']:
            for s in l['spans']:
                for c in s['chars']:
                    if 'Hyhwp' in s['font']: eqg.append(M.G(c['c'], c['bbox'], c['origin'], s['size']))
                    elif c['c'].strip() or True: other.append(c['bbox'])
    cl = M.cluster([g for g in eqg if g.y0 > 150 and g.y1 < 1075], other)
    cl.sort(key=lambda c: (min(g.y0 for g in c) // 40, min(g.x0 for g in c)))
    print('=== page', pn + 1, len(cl), 'clusters')
    for c in cl:
        x0 = min(g.x0 for g in c); y0 = min(g.y0 for g in c)
        print(f'({x0:.0f},{y0:.0f})', M.parse(c))
