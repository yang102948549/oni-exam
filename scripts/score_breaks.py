"""Compare line breaks of left passage + all columns between original PDF page and rebuilt PDF."""
import sys, pymupdf
def lines(path, page=0):
    p = pymupdf.open(path)[page]; out = []
    for b in p.get_text('dict')['blocks']:
        if b['type']: continue
        for l in b['lines']:
            t = ''.join(s['text'] for s in l['spans']).replace(' ', '')
            if t and 225 < l['bbox'][1] < 1070 and l['bbox'][0] < 790: out.append((l['bbox'][0] > 420, round(l['bbox'][1]), t))
    return out
def txt(path):
    L = lines(path); return [t for c in (False, True) for (cc, y, t) in sorted(L) if cc == c]
o = txt('국어.pdf'); r = txt(sys.argv[1])
so, sr = set(o), set(r)
print(sys.argv[1], 'orig lines', len(o), 'ours', len(r), 'identical lines', len(so & sr), f'{len(so&sr)/len(o):.0%}')
