"""Native HWPX first-page layout baseline, using a Hancom-generated seed.
Text is editable but positioned in independent single-line cells; this is NOT a
paragraph-reflow converter. Figures/rules are retained as a raster background.
"""
from pathlib import Path
import argparse,copy,json,zipfile,xml.etree.ElementTree as E
import pymupdf
NS={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph','hh':'http://www.hancom.co.kr/hwpml/2011/head','hc':'http://www.hancom.co.kr/hwpml/2011/core','hs':'http://www.hancom.co.kr/hwpml/2011/section','opf':'http://www.idpf.org/2007/opf/'}
for k,v in NS.items():E.register_namespace(k,v)
def q(prefix,name):return '{'+NS[prefix]+'}'+name

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--page',type=int,default=1);ap.add_argument('--calibration',type=Path);args=ap.parse_args()
 if args.page != 1:
  raise ValueError('This baseline has only been validated on Korean page 1.')
 out=Path('output/korean_exam_test');native=out/'native';native.mkdir(parents=True,exist_ok=True)
 pdf=pymupdf.open('국어.pdf');pg=pdf[0]
 pg.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(out/'source_page_01.png')
 background_doc=pymupdf.open('국어.pdf');background=background_doc[0]
 for b in background.get_text('dict')['blocks']:
  if b['type']==0:
   for line in b['lines']:
    for span in line['spans']:background.add_redact_annot(span['bbox'],fill=False)
 background.apply_redactions(images=0,graphics=0,text=0)
 background.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(native/'background.png')
 background_doc.close()
 for seed_name in ['sample.hwpx','picture.hwpx']:
  if not (native/seed_name).exists():
   raise FileNotFoundError('Run scripts/create_native_sample.py and scripts/create_picture_sample.py to create Hancom seeds.')
 lines=[];removed=[]
 for block in pg.get_text('dict')['blocks']:
  if block['type']!=0:continue
  for line in block['lines']:
   text=''.join(s['text'] for s in line['spans']).rstrip()
   if not text:continue
   box=list(line['bbox'])
   # First-page old header is occluded by the PDF's later white patch.
   if args.page==1 and box[1]<150 and box[0]<200:
    removed.append({'text':text,'reason':'visually_occluded_old_header'});continue
   if any(x['text']==text and abs(x['bbox'][0]-box[0])<1 and abs(x['bbox'][1]-box[1])<2 for x in lines):
    removed.append({'text':text,'reason':'duplicate_overlapping_text'});continue
   spans=line['spans'];size=max(s['size'] for s in spans)
   lines.append({'id':len(lines),'text':text,'bbox':box,'size':size,'font':spans[0]['font'],'color':spans[0]['color']})
 # HWPX objects follow source stream order; visual positions are independent.
 cal=json.loads(args.calibration.read_text(encoding='utf-8')) if args.calibration else {}
 with zipfile.ZipFile(native/'sample.hwpx') as z:seed={n:z.read(n) for n in z.namelist()}
 with zipfile.ZipFile(native/'picture.hwpx') as z:picseed={n:z.read(n) for n in z.namelist()}
 sec=E.fromstring(seed['Contents/section0.xml']);head=E.fromstring(seed['Contents/header.xml'])
 table=copy.deepcopy(sec.find('.//hp:tbl',NS));outer=sec.find('hp:p',NS)
 control=copy.deepcopy(outer.find('hp:run',NS))
 for child in list(sec):sec.remove(child)
 anchor=E.SubElement(sec,q('hp','p'),{'id':'0','paraPrIDRef':'0','styleIDRef':'0','pageBreak':'0','columnBreak':'0','merged':'0'})
 anchor.append(control)
 pp=control.find('.//hp:pagePr',NS);pp.set('width',str(round(pg.rect.width*100)));pp.set('height',str(round(pg.rect.height*100)))
 for k in pp.find('hp:margin',NS).attrib:pp.find('hp:margin',NS).set(k,'0')
 # Borderless cell fill and baseline paragraph formatting.
 paras=head.find('.//hh:paraProperties',NS)
 basepara=copy.deepcopy(paras[0]);basepara.set('id',str(len(paras)));basepara.set('snapToGrid','0');basepara.find('hh:align',NS).set('horizontal','LEFT')
 for e in basepara.findall('.//hh:lineSpacing',NS):e.set('type','PERCENT');e.set('value','100')
 paras.append(basepara);paras.set('itemCnt',str(len(paras)))
 charprops=head.find('.//hh:charProperties',NS);basechar=copy.deepcopy(charprops[0])
 fontfaces=head.find('.//hh:fontfaces',NS)
 for ff in fontfaces:
  ff[0].set('face','맑은 고딕');ff[1].set('face','신명조')
 pic=E.fromstring(picseed['Contents/section0.xml']).find('.//hp:pic',NS)
 pic.set('textWrap','BEHIND_TEXT');pic.set('zOrder','0')
 for name in ['orgSz','sz']:
  e=pic.find('hp:'+name,NS);e.set('width',str(round(pg.rect.width*100)));e.set('height',str(round(pg.rect.height*100)))
 for k,(x,y) in enumerate([(0,0),(pg.rect.width*100,0),(pg.rect.width*100,pg.rect.height*100),(0,pg.rect.height*100)]):
  e=pic.find('hp:imgRect/hc:pt'+str(k),NS);e.set('x',str(round(x)));e.set('y',str(round(y)))
 pos=pic.find('hp:pos',NS);pos.attrib.update({'treatAsChar':'0','vertRelTo':'PAPER','horzRelTo':'PAPER','vertOffset':'0','horzOffset':'0','flowWithText':'0','allowOverlap':'1'})
 run=E.SubElement(anchor,q('hp','run'),{'charPrIDRef':'0'});run.append(pic);E.SubElement(run,q('hp','t'))
 for item in lines:
  i=item['id'];text=item['text'];x,y,x1,y1=item['bbox'];s=item['size']
  fontid='0' if any(t in item['font'] for t in ['고딕','°íµñ','Gulim']) else '1'
  cp=copy.deepcopy(basechar);cid=len(charprops);cp.set('id',str(cid));cp.set('height',str(round(s*100)))
  cp.set('textColor',f"#{item['color']:06X}")
  for k in cp.find('hh:fontRef',NS).attrib:cp.find('hh:fontRef',NS).set(k,fontid)
  corr=cal.get(str(i),{});ratio=corr.get('ratio',90)
  for k in cp.find('hh:ratio',NS).attrib:cp.find('hh:ratio',NS).set(k,str(ratio))
  charprops.append(cp)
  tbl=copy.deepcopy(table);tbl.set('id',str(2000+i));tbl.set('zOrder',str(i+1));tbl.set('textWrap','IN_FRONT_OF_TEXT');tbl.set('borderFillIDRef','1');tbl.set('pageBreak','NONE')
  width=min(max(x1-x+12,35),pg.rect.width-x-1)
  height=s*1.25
  tbl.find('hp:sz',NS).attrib.update({'width':str(round(width*100)),'height':str(round(height*100))})
  tbl.find('hp:pos',NS).attrib.update({'treatAsChar':'0','vertRelTo':'PAPER','horzRelTo':'PAPER','vertOffset':str(round((y+corr.get('dy',-1))*100)),'horzOffset':str(round(x*100)),'flowWithText':'0','allowOverlap':'1'})
  for name in ['outMargin','inMargin']:
   for k in tbl.find('hp:'+name,NS).attrib:tbl.find('hp:'+name,NS).set(k,'0')
  cell=tbl.find('.//hp:tc',NS);cell.set('borderFillIDRef','1');cell.set('hasMargin','1')
  for k in cell.find('hp:cellMargin',NS).attrib:cell.find('hp:cellMargin',NS).set(k,'0')
  cell.find('hp:cellSz',NS).attrib.update({'width':str(round(width*100)),'height':str(round(height*100))})
  sub=cell.find('hp:subList',NS);sub.set('vertAlign','TOP')
  for child in list(sub):sub.remove(child)
  p=E.SubElement(sub,q('hp','p'),{'id':str(10000+i),'paraPrIDRef':basepara.get('id'),'styleIDRef':'0','pageBreak':'0','columnBreak':'0','merged':'0'})
  r=E.SubElement(p,q('hp','run'),{'charPrIDRef':str(cid)});E.SubElement(r,q('hp','t')).text=text
  r=E.SubElement(anchor,q('hp','run'),{'charPrIDRef':'0'});r.append(tbl);E.SubElement(r,q('hp','t'))
 charprops.set('itemCnt',str(len(charprops)))
 seed['Contents/section0.xml']=E.tostring(sec,encoding='utf-8',xml_declaration=True)
 seed['Contents/header.xml']=E.tostring(head,encoding='utf-8',xml_declaration=True)
 seed['BinData/image1.png']=(native/'background.png').read_bytes()
 manifest=E.fromstring(seed['Contents/content.hpf']);man=manifest.find('opf:manifest',NS)
 E.SubElement(man,q('opf','item'),{'id':'image1','href':'BinData/image1.png','media-type':'image/png','isEmbeded':'1'})
 seed['Contents/content.hpf']=E.tostring(manifest,encoding='utf-8',xml_declaration=True)
 seed['Preview/PrvText.txt']='\n'.join(x['text'] for x in lines).encode('utf-8')
 seed.pop('Preview/PrvImage.png',None)
 target=out/'국어_1페이지_변환시험.hwpx'
 with zipfile.ZipFile(target,'w') as z:
  for n,b in seed.items():z.writestr(n,b,compress_type=zipfile.ZIP_STORED if n=='mimetype' else zipfile.ZIP_DEFLATED)
 (out/'page01_extraction.json').write_text(json.dumps({'page':args.page,'lines':lines,'excluded':removed,'limitations':['fixed_line_cells','graphics_rasterized','paragraph_reflow_not_implemented']},ensure_ascii=False,indent=2),encoding='utf-8')
 print(target,len(lines),'editable lines',len(removed),'excluded',flush=True)
if __name__=='__main__':main()
