import importlib.util
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'desktop/engine'))
from ocr_layout import raw_from_ocr, structured_tables
import parsing


class ParsingTests(unittest.TestCase):
    def test_ocr_scale_confidence_and_rotation(self):
        page = {'scale': 3, 'width': 300, 'height': 600, 'lines': [
            {'text': '한글 ABC', 'confidence': .95, 'box': {'x': 30, 'y': 60, 'w': 150, 'h': 30}},
            {'text': 'noise', 'confidence': .2, 'box': {'x': 0, 'y': 0, 'w': 10, 'h': 10}}]}
        raw, dropped = raw_from_ocr(page, 100, 200)
        line = raw['blocks'][0]['lines'][0]
        self.assertEqual(line['bbox'], [10, 20, 60, 30])
        self.assertEqual(''.join(c['c'] for c in line['spans'][0]['chars']), '한글 ABC')
        self.assertEqual(dropped, 1)
        page['deskewAngle'] = 5
        rotated, _ = raw_from_ocr(page, 100, 200)
        self.assertNotEqual(rotated['blocks'][0]['lines'][0]['bbox'], line['bbox'])
        page['scale'] = 0
        with self.assertRaises(ValueError): raw_from_ocr(page, 100, 200)

    def test_routing_requires_two_columns(self):
        with pymupdf.open() as doc:
            p = doc.new_page(width=842, height=1191)
            for y in range(270, 500, 25): p.insert_text((88, y), 'Left column text')
            self.assertFalse(parsing.exam_layout(doc, 1, 1))
            for y in range(270, 500, 25): p.insert_text((437, y), 'Right column text')
            self.assertTrue(parsing.exam_layout(doc, 1, 1))
            doc.new_page(width=595, height=842)
            self.assertFalse(parsing.exam_layout(doc, 1, 2))

    def test_tables_preserve_content_and_reject_spans(self):
        cells = [[{'text': f'{r}/{c}', 'colSpan': 1, 'rowSpan': 1} for c in range(2)] for r in range(2)]
        b = {'type': 'table', 'pageNumber': 2, 'bbox': {'x': 88, 'y': 600, 'width': 300, 'height': 90},
             'table': {'rows': 2, 'cols': 2, 'cells': cells}}
        grids = structured_tables([b], 2, 1191, 150)
        self.assertEqual(grids[0]['rect'].y0, 501)
        self.assertEqual(grids[0]['cells'][1][1][0]['t'], '1/1')
        cells[0][0]['colSpan'] = 2
        self.assertEqual(structured_tables([b], 2, 1191, 150), [])

    def test_ocr_failure_does_not_succeed_with_empty_page(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); source = root / 'scan.pdf'
            with pymupdf.open() as d:
                d.new_page(width=842, height=1191); d.save(source)
            with patch.object(parsing, 'parse', return_value={'success': True, 'pageQuality': [], 'ocrLines': []}):
                with self.assertRaisesRegex(ValueError, 'OCR'):
                    parsing.prepare(source, 1, 1, root, root, 'auto', lambda *a, **k: None)


if __name__ == '__main__': unittest.main()
