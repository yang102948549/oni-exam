"""Opt-in real OCR smoke: rasterize a source page and convert without altering it."""
import json
from pathlib import Path
import sys
import pymupdf

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / 'engine'))
import worker

root = APP / '.test-data' / 'ocr-smoke'
root.mkdir(parents=True, exist_ok=True)
source = APP.parent / '국어.pdf'
scan = root / 'scan.pdf'
with pymupdf.open(source) as doc, pymupdf.open() as out:
    page = doc[0]
    p = out.new_page(width=page.rect.width, height=page.rect.height)
    p.insert_image(p.rect, stream=page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes('png'))
    out.save(scan)
result = worker.handle({'action': 'convert', 'path': str(scan), 'first': 1, 'last': 1,
                        'subject': '국어', 'math': False, 'ocr': 'auto',
                        'dataDir': str(root / 'data'), 'outputDir': str(root)})
print(json.dumps(result, ensure_ascii=False))
