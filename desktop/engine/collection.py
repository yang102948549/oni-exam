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


def _cell(html):
    # A <br> inside a cell is a line wrap in the PDF, usually mid-word in Korean.
    text = re.sub(r'(?i)<br\s*/?>', '', html)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return re.sub(r'\s+', ' ', text).strip()


def plain_text(markdown):
    """Turn kordoc markdown (tables come as HTML) into 'label: value' lines."""
    def table(m):
        lines = []
        for row in re.findall(r'(?is)<tr[^>]*>(.*?)</tr>', m.group(0)):
            cells = [c for c in (_cell(x) for x in re.findall(r'(?is)<t[dh][^>]*>(.*?)</t[dh]>', row)) if c]
            if len(cells) >= 2:
                lines.append(cells[0].rstrip(' :：') + ': ' + ' '.join(cells[1:]))
            elif cells:
                lines.append(cells[0])
        return '\n'.join(lines)
    text = re.sub(r'(?is)<table[^>]*>.*?</table>', table, markdown)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)       # image placeholders
    text = re.sub(r'(?m)^#+\s*', '', text).replace('\\~', '~')
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


TRAINING_LABELS = ['연수과정명', '교육과정명', '과정명', '연수명', '연수과정', '교육명', '교육과정']
PERSON_LABELS = [r'성\s*명', r'이\s*름', '이수자', '수료자']


def _clean(value):
    value = value.strip(' *:：·')
    if value.count(')') > value.count('('):    # '...(연수명 : X)' leaves a stray ')'
        value = value[::-1].replace(')', '', 1)[::-1].rstrip()
    return value[:100]


def labeled(text, labels):
    # Prefer a label that starts a line (table rows, form lines), then anywhere.
    for anchor in (r'(?m)^\s*', r''):
        for label in labels:
            match = re.search(anchor + r'(?:' + label + r')\s*[:：]?\s*([^\n]+)', text)
            if match and _clean(match.group(1)):
                return _clean(match.group(1))
    return ''


def certificate_fields(text):
    person = labeled(text, PERSON_LABELS)
    return {'training': labeled(text, TRAINING_LABELS), 'person': person.split()[0] if person else ''}


def needs_ocr(path):
    """OCR only when some page has no text layer; stamps and logos do not count."""
    with pymupdf.open(path) as doc:
        return len(doc), any(not page.get_text().strip() for page in doc)


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
            count, scanned = needs_ocr(path)
            with tempfile.TemporaryDirectory(dir=data_dir) as t:
                result = parsing.parse(path, f'1-{count}', Path(t), data_dir, readOnly=scanned)
                if not scanned and any(p.get('needsOcr') for p in result.get('pageQuality', [])):
                    result = parsing.parse(path, f'1-{count}', Path(t), data_dir, readOnly=True)
            text = plain_text(result.get('markdown', ''))
            row.update(**certificate_fields(text),
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
