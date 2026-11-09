from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import collection

# Shapes taken from real certificates parsed by kordoc (names replaced).
TABLE = '''제 단재교-원격직무(상시)-2026-117038 호

# 이수증

<table>
<tr><th colspan="2"></th></tr>
<tr><td>과정명:</td><td rowspan="2">교직원을 위한 법정의무교육(공무원 행동<br>강령 교육)</td></tr>
<tr><td></td></tr>
<tr><td>성명:</td><td>홍길동</td></tr>
<tr><td>연수기간:</td><td>2026.07.13.~2026.07.13.</td></tr>
</table>

![image](image_001.png)'''

FREE_TEXT = '''# 교육연수 이수증

성 명 홍길동

연수목적

2025년 AI·디지털 기반 교육혁신 선도교사 양성을 위한 연수 (연수명 :2025년 AI·디지털 기반 교육혁신 선도교사 양성 연수)'''

OCR_SCAN = '''# 교육연수이수증

성 명:홍길동

생년월일: 1988.10.30

연수종별:직무

연수과정: AI와 함께하는웹코딩 기초

연수기간:2025년05월 14일\\~2025년12월23일'''


class CertificateFieldTests(unittest.TestCase):
    def test_html_table_rows_become_label_value_lines(self):
        text = collection.plain_text(TABLE)
        self.assertNotIn('<', text)
        self.assertNotIn('image_001', text)
        self.assertEqual(collection.certificate_fields(text),
                         {'training': '교직원을 위한 법정의무교육(공무원 행동강령 교육)', 'person': '홍길동'})

    def test_label_inside_sentence_drops_stray_parenthesis(self):
        fields = collection.certificate_fields(collection.plain_text(FREE_TEXT))
        self.assertEqual(fields, {'training': '2025년 AI·디지털 기반 교육혁신 선도교사 양성 연수', 'person': '홍길동'})

    def test_ocr_text_uses_yeonsu_gwajeong_label(self):
        fields = collection.certificate_fields(collection.plain_text(OCR_SCAN))
        self.assertEqual(fields, {'training': 'AI와 함께하는웹코딩 기초', 'person': '홍길동'})

    def test_missing_labels_stay_empty_for_review(self):
        self.assertEqual(collection.certificate_fields('위와 같이 이수하였음을 증명합니다.'), {'training': '', 'person': ''})

    def test_clean_values_make_clean_file_names(self):
        fields = collection.certificate_fields(collection.plain_text(TABLE))
        with tempfile.TemporaryDirectory() as t:
            source = Path(t) / 'in.pdf'
            with pymupdf.open() as doc:
                doc.new_page(); doc.save(source)
            out = Path(t) / 'out'
            result = collection.save({'kind': 'certificate', 'outputDir': str(out),
                                      'rows': [{'path': str(source), **fields}]})
            self.assertEqual(result[0]['error'], '')
            self.assertEqual(Path(result[0]['path']).relative_to(out).as_posix(),
                             '교직원을 위한 법정의무교육(공무원 행동강령 교육)/교직원을 위한 법정의무교육(공무원 행동강령 교육)(홍길동).pdf')


class OcrRoutingTests(unittest.TestCase):
    def run_analyze(self, make_page, quality):
        calls = []
        def fake_parse(path, pages, temp, data_dir, **options):
            calls.append(options.get('readOnly', False))
            return {'markdown': TABLE, 'pageQuality': [{'page': 1, 'needsOcr': quality and not calls[-1]}]}
        with tempfile.TemporaryDirectory() as t, patch.object(collection.parsing, 'parse', fake_parse):
            pdf = Path(t) / 'a.pdf'
            with pymupdf.open() as doc:
                make_page(doc.new_page()); doc.save(pdf)
            row = collection.analyze({'paths': [str(pdf)]}, Path(t) / 'data', lambda *a, **k: None)[0]
        self.assertEqual(row['person'], '홍길동')
        return calls

    def test_text_pdf_skips_ocr(self):
        self.assertEqual(self.run_analyze(lambda p: p.insert_text((72, 72), 'Certificate'), False), [False])

    def test_page_without_text_uses_ocr(self):
        self.assertEqual(self.run_analyze(lambda p: None, False), [True])

    def test_broken_text_layer_falls_back_to_ocr(self):
        self.assertEqual(self.run_analyze(lambda p: p.insert_text((72, 72), 'garbled'), True), [False, True])


if __name__ == '__main__':
    unittest.main()
