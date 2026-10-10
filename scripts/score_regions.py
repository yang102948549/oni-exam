import sys, pymupdf
def lines(path):
    p = pymupdf.open(path)[0]; out = []
    for b in p.get_text('dict')['blocks']:
        if b['type']: continue
        for l in b['lines']:
            t = ''.join(s['text'] for s in l['spans']).replace(' ', '')
            if t and 225 < l['bbox'][1] < 1075: out.append((l['bbox'][0], l['bbox'][1], t))
    return out
def region(L, name):
    f = {'passage': lambda x, y: x < 420 and y < 860, 'leftQ': lambda x, y: x < 420 and y >= 860,
         'rightChoice': lambda x, y: x >= 420 and (y < 520 or y > 860), 'bogi': lambda x, y: x >= 420 and 600 < y < 860}[name]
    return {t for x, y, t in L if f(x, y)}
o = lines('국어.pdf'); r = lines(sys.argv[1])
print(sys.argv[1].split('_')[-1], ' '.join(f"{n}:{len(region(o,n)&region(r,n))}/{len(region(o,n))}" for n in ['passage', 'leftQ', 'rightChoice', 'bogi']))
