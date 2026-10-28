"""Local NDJSON bridge. No network, no shell, no Hancom process termination."""
from __future__ import annotations

import base64
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import sqlite3
import sys
import tempfile
import traceback
import uuid
import zipfile
import xml.etree.ElementTree as ET

import pymupdf

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
FONTS = ['KoPub World 바탕체', 'KoPub World 돋움체', 'KoPub World 돋움체', 'HyhwpEQ']
SUBJECTS = {'국어', '영어', '수학', '한국사', '사회탐구', '과학탐구'}


def emit(kind, **kw):
    print(json.dumps({'type': kind, **kw}, ensure_ascii=False), flush=True)


@contextlib.contextmanager
def database(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(data_dir / 'workspace.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, name TEXT, source TEXT, output TEXT, subject TEXT, first_page INTEGER, last_page INTEGER, created_at TEXT, status TEXT, message TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
    try:
        with db:
            yield db
    finally:
        db.close()


def pdf_file(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file() or p.suffix.lower() != '.pdf':
        raise ValueError('PDF 파일을 선택해 주세요.')
    if p.stat().st_size > 300 * 1024 * 1024:
        raise ValueError('300MB 이하의 PDF를 선택해 주세요.')
    d = pymupdf.open(p)
    if d.needs_pass:
        d.close()
        raise ValueError('암호가 설정된 PDF입니다. 암호를 해제한 파일을 선택해 주세요.')
    if not d.page_count:
        d.close()
        raise ValueError('페이지가 없는 PDF입니다.')
    return p, d


def thumbnail(doc, page):
    if not 1 <= page <= len(doc):
        raise ValueError('미리보기 페이지 범위가 올바르지 않습니다.')
    p = doc[page - 1]
    pix = p.get_pixmap(matrix=pymupdf.Matrix(760 / p.rect.width, 760 / p.rect.width), alpha=False)
    return 'data:image/png;base64,' + base64.b64encode(pix.tobytes('png')).decode('ascii')


def inspect(req):
    p, d = pdf_file(req['path'])
    with d:
        text = '\n'.join(d[i].get_text() for i in range(min(3, len(d)))).strip()
        search = p.stem + ' ' + text[:1600]
        subject = next((s for s in ['영어', '수학', '한국사', '과학탐구', '사회탐구', '국어'] if s in search), '국어')
        sizes = [(round(x.rect.width), round(x.rect.height)) for x in d]
        compatible = all(abs(w - 842) <= 8 and abs(h - 1191) <= 8 for w, h in sizes)
        warnings = []
        if not text: warnings.append('이미지로 된 PDF입니다. 현재 버전은 텍스트가 포함된 시험지 PDF를 지원합니다.')
        if not compatible: warnings.append('현재 변환기는 842 × 1191pt 크기의 수능형 2단 문제지에 맞춰져 있습니다. 다른 판형은 변환을 지원하지 않습니다.')
        return {'path': str(p), 'name': p.name, 'size': p.stat().st_size, 'pages': len(d), 'subject': subject,
                'hasText': bool(text), 'compatible': compatible, 'warnings': warnings, 'thumbnail': thumbnail(d, 1)}


def run_script(name, args):
    old = sys.argv
    sys.argv = [str(ROOT / 'scripts' / name), *map(str, args)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(sys.argv[0], run_name='__main__')
    finally:
        sys.argv = old


def convert(req, data_dir):
    source, doc = pdf_file(req['path'])
    first, last = int(req['first']), int(req['last'])
    subject = req.get('subject', '국어')
    if subject not in SUBJECTS:
        doc.close()
        raise ValueError('지원하지 않는 과목입니다.')
    with doc:
        if not 1 <= first <= last <= len(doc):
            raise ValueError(f'페이지 범위는 1~{len(doc)} 안에서 지정해 주세요.')
        for i in range(first - 1, last):
            p = doc[i]
            if abs(p.rect.width - 842) > 8 or abs(p.rect.height - 1191) > 8:
                raise ValueError(f'{i + 1}쪽은 지원하는 수능형 판형이 아닙니다.')
            if not p.get_text().strip():
                raise ValueError(f'{i + 1}쪽에 추출할 텍스트가 없습니다. 스캔 PDF는 아직 지원하지 않습니다.')
    output_dir = Path(req['outputDir']).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', source.stem).strip('. ')[:90] or '문제지'
    target = output_dir / f'{name}_{first}-{last}쪽_{stamp}_{job_id[:6]}.hwpx'
    created = datetime.now(timezone.utc).isoformat()
    with database(data_dir) as db:
        db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)', (job_id, source.name, str(source), str(target), subject, first, last, created, 'running', '변환 중'))
    try:
        with tempfile.TemporaryDirectory(prefix='oni-', dir=data_dir) as temp:
            temp = Path(temp)
            items = temp / 'items.json'
            emit('progress', stage='extract', percent=20, message='문항과 지문을 분석하고 있어요.')
            lang = 'en' if subject == '영어' else 'soc' if subject in {'사회탐구', '과학탐구', '한국사'} else 'ko'
            extract_args = [source, first, last, items, '--lang', lang, '--figdir', temp / 'figures']
            if req.get('math', subject in {'수학', '과학탐구'}): extract_args.append('--math')
            run_script('extract_items4.py', extract_args)
            blocks = json.loads(items.read_text(encoding='utf-8'))
            if not blocks:
                raise ValueError('변환할 문항을 찾지 못했습니다. 수능형 2단 문제지인지 확인해 주세요.')
            pages_found = {b['page'] for b in blocks}
            missing = [p for p in range(first, last + 1) if p not in pages_found]
            if missing:
                raise ValueError(f'문항을 찾지 못한 페이지가 있습니다: {missing}. 변환 범위를 확인해 주세요.')
            emit('progress', stage='build', percent=60, message=f'{len(blocks)}개 문항·지문 블록을 조판하고 있어요.')
            built = temp / 'result.hwpx'
            build_args = ['--items', items, '--out', built, '--subject', subject, '--total', last - first + 1,
                          '--title', str(req.get('title', '수능형 연습 문제지'))[:60],
                          '--period', {'국어': '제1 교시', '수학': '제2 교시', '영어': '제3 교시'}.get(subject, '제4 교시'),
                          '--lang', 'en' if subject == '영어' else 'ko', '--credit', 'Oni Exam']
            if subject in {'사회탐구', '과학탐구', '한국사'}:
                build_args += ['--preset', 'soc', '--area', subject, '--sub', req.get('subtitle', '')[:60]]
            run_script('build_hwpx_doc4.py', build_args)
            emit('progress', stage='verify', percent=90, message='문서 구조와 저장 파일을 확인하고 있어요.')
            with zipfile.ZipFile(built) as z:
                if z.testzip() is not None: raise ValueError('생성 문서가 손상되었습니다.')
                for entry in z.namelist():
                    if entry.endswith('.xml'): ET.fromstring(z.read(entry))
            # Exclusive create prevents replacing any existing document, including concurrent jobs.
            with target.open('xb') as f:
                try:
                    with built.open('rb') as src: shutil.copyfileobj(src, f)
                except Exception:
                    f.close()
                    target.unlink()
                    raise
        with database(data_dir) as db:
            db.execute('UPDATE jobs SET status=?, message=? WHERE id=?', ('done', f'{len(blocks)}개 블록 · 한글에서 최종 배치를 확인해 주세요.', job_id))
            result = dict(db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())
        emit('progress', stage='done', percent=100, message='문제지가 완성되었어요.')
        return result
    except Exception as e:
        with database(data_dir) as db:
            db.execute('UPDATE jobs SET status=?, message=? WHERE id=?', ('failed', str(e), job_id))
        raise


def environment():
    names = []
    hancom = False
    if sys.platform == 'win32':
        import winreg
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                with winreg.OpenKey(hive, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as k:
                    for i in range(winreg.QueryInfoKey(k)[1]): names.append(winreg.EnumValue(k, i)[0])
            except OSError: pass
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'HWPFrame.HwpObject\CLSID'): hancom = True
        except OSError: pass
    norm = lambda s: re.sub(r'[\s_-]', '', s).lower()
    aliases = [['kopubworld바탕', 'kopubworldbatang'], ['kopubworld돋움', 'kopubworlddotum'], ['kopubworld돋움', 'kopubworlddotum'], ['hyhwpeq']]
    return {'hancom': hancom, 'fonts': [{'name': f, 'installed': any(any(a in norm(n) for a in aa) for n in names)} for f, aa in zip(FONTS, aliases)], 'engine': pymupdf.VersionBind}


def handle(req):
    data_dir = Path(req['dataDir']).resolve()
    action = req['action']
    if action == 'inspect': return inspect(req)
    if action == 'preview':
        _, d = pdf_file(req['path'])
        with d: return {'thumbnail': thumbnail(d, int(req['page']))}
    if action == 'convert': return convert(req, data_dir)
    if action == 'environment': return environment()
    with database(data_dir) as db:
        if action == 'history':
            return [dict(row) for row in db.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 200')]
        if action == 'save_settings':
            value = {'outputDir': str(req.get('value', {}).get('outputDir', ''))}
            db.execute('INSERT OR REPLACE INTO settings VALUES (1,?)', (json.dumps(value),))
            return value
        if action == 'settings':
            row = db.execute('SELECT value FROM settings WHERE id=1').fetchone()
            return json.loads(row[0]) if row else {'outputDir': ''}
    raise ValueError('지원하지 않는 작업입니다.')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stdin, 'reconfigure'): sys.stdin.reconfigure(encoding='utf-8')
    try:
        request = json.loads(sys.stdin.readline())
        emit('result', data=handle(request))
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        emit('error', message=str(exc))
        sys.exit(1)
