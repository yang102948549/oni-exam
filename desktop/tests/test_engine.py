import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
import pymupdf

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('worker', APP / 'engine/worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / 'data'

    def tearDown(self): self.tmp.cleanup()

    def pdf(self, name='문제 & 시험지.pdf', width=842, height=1191, text=True):
        path = self.root / name
        with pymupdf.open() as d:
            p = d.new_page(width=width, height=height)
            if text:
                p.insert_text((88, 270), '1. Read the following passage.', fontsize=12)
                p.insert_text((88, 300), 'This is a test passage for a local examination.', fontsize=11)
                p.insert_text((88, 330), 'Choose the correct answer.', fontsize=11)
            d.save(path)
        return path

    def call(self, action, **kw):
        with contextlib.redirect_stdout(io.StringIO()):
            return worker.handle({'action': action, 'dataDir': str(self.data), **kw})

    def test_metadata_and_preview(self):
        p = self.pdf()
        info = self.call('inspect', path=str(p))
        self.assertEqual(info['pages'], 1)
        self.assertTrue(info['compatible'])
        self.assertTrue(info['thumbnail'].startswith('data:image/png;base64,'))
        with self.assertRaises(ValueError): self.call('preview', path=str(p), page=2)

    def test_scan_and_wrong_page_size(self):
        p = self.pdf(text=False)
        self.assertFalse(self.call('inspect', path=str(p))['hasText'])
        with self.assertRaises(ValueError): self.call('convert', path=str(p), first=1, last=1, subject='국어', outputDir=str(self.root / 'out'))
        q = self.pdf(name='a4.pdf', width=595, height=842)
        self.assertFalse(self.call('inspect', path=str(q))['compatible'])

    def test_conversion_valid_xml_fonts_history_and_no_overwrite(self):
        p = self.pdf()
        original = p.read_bytes()
        kwargs = dict(path=str(p), first=1, last=1, subject='영어', math=False, outputDir=str(self.root / '결과'))
        result = self.call('convert', **kwargs)
        self.assertEqual(result['status'], 'done')
        with zipfile.ZipFile(result['output']) as z:
            header = ET.fromstring(z.read('Contents/header.xml'))
            for name in z.namelist():
                if name.endswith('.xml'): ET.fromstring(z.read(name))
            faces = {n.attrib['face'] for n in header.iter() if n.tag.endswith('}font')}
            self.assertTrue(set(worker.FONTS).issubset(faces))
        env = self.call('install_fonts')
        self.assertEqual([f['name'] for f in env['fonts']], worker.FONTS)
        self.assertTrue(all(f['installed'] for f in env['fonts']))
        second = self.call('convert', **kwargs)
        self.assertNotEqual(result['output'], second['output'])
        self.assertEqual(p.read_bytes(), original)
        self.assertEqual(len(self.call('history')), 2)
        self.assertTrue(Path(result['output']).exists())

    def test_range_and_settings(self):
        p = self.pdf()
        with self.assertRaises(ValueError): self.call('convert', path=str(p), first=2, last=1, outputDir=str(self.root))
        self.call('save_settings', value={'outputDir': str(self.root)})
        self.assertEqual(self.call('settings')['outputDir'], str(self.root))
        self.assertGreater(worker._ver_tuple('0.2.0'), worker._ver_tuple('0.1.0'))
        with self.assertRaises(ValueError):
            self.call('install_update', downloadUrl='https://example.com/evil.exe')


if __name__ == '__main__': unittest.main()
