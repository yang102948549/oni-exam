"""Measure text widths/positions from Hancom output for the one-page baseline."""
from pathlib import Path
import json,re
import pymupdf
out=Path('output/korean_exam_test');data=json.loads((out/'page01_extraction.json').read_text(encoding='utf-8'))
p=pymupdf.open(out/'국어_1페이지_한글렌더.pdf');chars=[]
for b in p[0].get_text('rawdict')['blocks']:
 if b['type']!=0:continue
 for line in b['lines']:
  for s in line['spans']:
   for c in s['chars']:
    if not c['c'].isspace():chars.append(c)
text=''.join(c['c'] for c in chars);cursor=0;cal={};missing=[]
for item in data['lines']:
 needle=re.sub(r'\s+','',item['text']);pos=text.find(needle,cursor)
 if pos<0:pos=text.find(needle)
 if pos<0:missing.append(item['id']);continue
 cc=chars[pos:pos+len(needle)];cursor=pos+len(needle)
 rows={}
 for c in cc:rows.setdefault(round(c['origin'][1],1),[]).append(c)
 total=sum(max(c['bbox'][2] for c in row)-min(c['bbox'][0] for c in row) for row in rows.values())
 target=item['bbox'][2]-item['bbox'][0]
 ratio=max(50,min(150,round(90*target/total))) if total else 90
 actual_y=min(c['bbox'][1] for c in cc)
 cal[str(item['id'])]={'ratio':ratio,'dy':round(-1+item['bbox'][1]-actual_y,3),'render_line_count':len(rows)}
(out/'calibration.json').write_text(json.dumps(cal,ensure_ascii=False,indent=2),encoding='utf-8')
print('matched',len(cal),'missing',missing,'wrapped',[(k,v['render_line_count']) for k,v in cal.items() if v['render_line_count']>1])
