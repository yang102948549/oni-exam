"""원본과 같은 블록 간 거리가 되도록 문단 앞 간격을 반복 보정한다(블록마다, 같은 단 안에서).
usage: python -X utf8 scripts/calibrate_spacing.py ITEMS.json OUT.hwpx -- <build args...>
"""
import json, re, subprocess, sys
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parent.parent
items, out = Path(sys.argv[1]), Path(sys.argv[2])
bargs = sys.argv[sys.argv.index('--') + 1:]
adjf = out.with_suffix('.adj.json'); adj = {}
blocks = json.loads(items.read_text(encoding='utf-8'))
TEXT_TYPES = ('stem', 'stemcont', 'choice_row', 'bogi_title', 'bogi_item', 'passage', 'bogi', 'choice', 'label', 'qbox', 'instr')

def norm(s): return ''.join(ch for ch in s if not ch.isspace() and ord(ch) < 0xE000)

def prefix(b):
    t = norm(b.get('text', ''))
    return t[:6] if len(t) >= 3 else None

cand = [b for b in blocks if b['type'] in TEXT_TYPES and prefix(b)]

def our_lines(pdf):
    d = pymupdf.open(str(pdf)); seq = []
    for pi, pg in enumerate(d):
        for col in (0, 1):
            ls = []
            for blk in pg.get_text('dict')['blocks']:
                if blk['type']: continue
                for l in blk['lines']:
                    if l['bbox'][1] > 150 and l['bbox'][3] < 1080 and (l['bbox'][0] >= 421) == bool(col):
                        t = norm(''.join(s['text'] for s in l['spans']))
                        if t: ls.append((l['bbox'][1], t))
            ls.sort()
            seq += [(pi, col, y, t) for y, t in ls]
    return seq, len(d)

def key(b): return f"{b['page']}-{b['col']}-{round(b['y0'])}"

import os
for it in range(int(os.environ.get('ITERS', 8))):
    adjf.write_text(json.dumps(adj, ensure_ascii=False), encoding='utf-8')
    subprocess.run(['taskkill', '/F', '/IM', 'Hwp.exe'], capture_output=True)
    subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/build_hwpx_doc4.py'), '--items', str(items), '--adj', str(adjf), '--out', str(out)] + bargs,
                   check=True, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/render_retry.py'), str(out), '3'], capture_output=True)
    seq, npages = our_lines(out.with_suffix('.pdf'))
    # 블록을 흐름 순서대로 우리 줄에 대응
    pos = {}; cur = 0
    for b in cand:
        pre = prefix(b)
        for j in range(cur, min(cur + 40, len(seq))):
            if seq[j][3].startswith(pre):
                pos[id(b)] = seq[j][:3]; cur = j + 1; break
    new = dict(adj); worst = 0.0; pairs = 0; wp = None
    for b0, b1 in zip(cand, cand[1:]):
        if id(b0) not in pos or id(b1) not in pos: continue
        if (b0['page'], b0['col']) != (b1['page'], b1['col']) or pos[id(b0)][:2] != pos[id(b1)][:2]: continue
        err = (pos[id(b1)][2] - pos[id(b0)][2]) - (b1['y0'] - b0['y0'])
        if abs(err) > worst: worst = abs(err); wp = (b0['type'], b1['type'], b0['text'][:14], b1['text'][:14], round(err, 1), round(b1['y0'] - b0['y0'], 1))
        pairs += 1
        if abs(err) > 0.8: new[key(b1)] = new.get(key(b1), 0.0) - err
    print(f'iter {it}: pages {npages}, worst error {worst:.1f}pt, pairs {pairs}, matched {len(pos)}/{len(cand)}', wp, flush=True)
    if worst < 2.0 and npages == len({b['page'] for b in blocks}): break
    adj = {k: round(v, 1) for k, v in new.items()}
adjf.write_text(json.dumps(adj, ensure_ascii=False), encoding='utf-8')
print('final adj file:', adjf)
