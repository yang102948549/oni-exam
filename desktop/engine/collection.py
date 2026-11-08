"""Local document collection; uncertain fields require human review."""
import re
import shutil
import tempfile
from pathlib import Path
import parsing
import pymupdf


def field(text, labels):
    match = re.search(r'(?:' + labels + r')\s*[:：|]?\s*([^\n|]+)', text)
    return match.group(1).strip(' *:：')[:100] if match else ''


def analyze(req, data_dir, emit):
    data_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    paths = req.get('paths', [])
    if not paths or len(paths) > 100:
        raise ValueError('PDF를 1~100개 선택해 주세요.')
    for i, value in enumerate(paths):
        path = Path(value).resolve()
        emit('progress', stage='collect', percent=int(i*100/len(paths)), message=f'{i+1}/{len(paths)} 파일을 읽고 있어요.')
        row = {'path': str(path), 'name': path.name, 'training': '', 'person': '', 'date': '', 'vendor': '', 'amount': '', 'error': ''}
        try:
            if path.suffix.lower() != '.pdf' or not path.is_file() or path.stat().st_size > 300*1024*1024:
                raise ValueError('300MB 이하 PDF만 지원합니다.')
            with tempfile.TemporaryDirectory(dir=data_dir) as t:
                with pymupdf.open(path) as doc:
                    count = len(doc)
                result = parsing.parse(path, f'1-{count}', Path(t), data_dir, readOnly=True)
            text = result.get('markdown', '')
            row.update(training=field(text, '연수명|과정명|교육명|교육과정'), person=field(text, '성\\s*명|이\\s*름|수료자|이수자'),
                       vendor=field(text, '상호명|상호|가맹점명'), amount=field(text, '합계금액|결제금액|총액|합계'))
            date = re.search(r'(20\d{2})[./년-]\s*(\d{1,2})[./월-]\s*(\d{1,2})', text)
            if date: row['date'] = f'{date[1]}-{int(date[2]):02}-{int(date[3]):02}'
            row['text'] = text[:20000]
        except Exception as e:
            row['error'] = str(e)
        rows.append(row)
    return rows


def safe(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(value)).strip(' .')[:100]
    if not value or value in ('.', '..') or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM\d|LPT\d)(\..*)?', value):
        raise ValueError('저장 이름을 확인해 주세요.')
    return value


def save(req):
    root = Path(req['outputDir']).resolve()
    results = []
    for row in req.get('rows', []):
        try:
            source = Path(row['path']).resolve()
            if source.suffix.lower() != '.pdf' or not source.is_file(): raise ValueError('원본 PDF가 없습니다.')
            if req.get('kind') == 'receipt':
                folder = safe(row['date'][:7])
                name = safe(f"{row['date']}_{row['vendor']}_{row['amount']}")
                if not all(row.get(k) for k in ('date', 'vendor', 'amount')): raise ValueError('날짜·사용처·금액을 입력해 주세요.')
            else:
                folder = safe(row['training']); name = safe(f"{folder}({safe(row['person'])})")
            directory = root / folder
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / (name + '.pdf')
            # Exclusive creation: duplicates are reported, never overwritten.
            with target.open('xb') as dst:
                try:
                    with source.open('rb') as src: shutil.copyfileobj(src, dst)
                except Exception:
                    dst.close(); target.unlink(); raise
            results.append({'path': str(target), 'error': ''})
        except Exception as e:
            results.append({'path': row.get('path', ''), 'error': str(e)})
    return results
