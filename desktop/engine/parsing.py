"""Pinned kordoc quality/OCR stage, followed by the exam layout adapter."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def runtime():
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent / 'kordoc-runtime'
    else:
        base = Path(__file__).parent / 'kordoc'
    node = base / 'node.exe'
    executable = str(node) if node.is_file() else shutil.which('node')
    if not executable or not (base / 'node_modules/kordoc/package.json').is_file():
        raise ValueError('kordoc 엔진이 없습니다. 개발 환경은 npm run parser:install, 배포 앱은 재설치가 필요합니다.')
    return executable, base


def parse(source, pages, temp, data_dir, force=False, **options):
    node, base = runtime()
    request, output = temp / 'parse-request.json', temp / 'parse-result.json'
    output.unlink(missing_ok=True)
    request.write_text(json.dumps({'path': str(source), 'pages': pages, 'force': force,
                                  'output': str(output), **options}, ensure_ascii=False), encoding='utf-8')
    env = os.environ.copy()
    env['KORDOC_MODEL_CACHE'] = str(data_dir / 'ocr-models')
    try:
        result = subprocess.run([node, str(base / 'parse.mjs'), str(request)],
                                capture_output=True, timeout=600, env=env,
                                creationflags=0x08000000 if sys.platform == 'win32' else 0)
    except subprocess.TimeoutExpired as e:
        raise ValueError('문서 분석이 10분을 초과했습니다. 페이지 범위를 줄여 다시 시도해 주세요.') from e
    if not output.is_file():
        raise ValueError('kordoc 분석 프로세스가 결과를 반환하지 못했습니다.')
    payload = json.loads(output.read_text(encoding='utf-8'))
    if result.returncode or not payload.get('success'):
        raise ValueError('kordoc 분석 실패: ' + str(payload.get('error', '알 수 없는 오류'))[:500])
    return payload


def exam_layout(doc, first, last):
    """Conservative auto routing: matching paper AND text in two body columns.

    A scan without text cannot be classified reliably; it uses general mode
    unless the user explicitly chooses the exam template.
    """
    for i in range(first-1, last):
        page = doc[i]
        if abs(page.rect.width-842) > 8 or abs(page.rect.height-1191) > 8:
            return False
        spans = [l['bbox'] for b in page.get_text('dict')['blocks'] if b['type'] == 0
                 for l in b['lines'] if 245 < l['bbox'][1] < 1075]
        left = [b for b in spans if 65 < b[0] < 410 and b[2] < 425]
        right = [b for b in spans if 425 < b[0] < 765]
        crossing = [b for b in spans if b[0] < 400 and b[2] > 440]
        if len(left) < 5 or len(right) < 5 or len(crossing) > len(spans)*0.1:
            return False
    return True


def general(source, first, last, temp, data_dir, mode, math, emit):
    if mode not in ('auto', 'off', 'force'):
        raise ValueError('OCR 모드는 auto, off, force 중 하나여야 합니다.')
    emit('progress', stage='analyze', percent=15,
         message='문단·표·그림을 분석하고 있어요. 스캔 페이지는 OCR로 읽습니다.')
    built = temp / 'result.hwpx'
    result = parse(source, f'{first}-{last}', temp, data_dir, force=mode == 'force',
                   general=True, ocr=mode, math=math, hwpx=str(built))
    warnings = ['일반 문서 모드: A4 1단으로 재구성됩니다. 원본의 단 배치·쪽 나눔과 다를 수 있습니다.']
    warnings.extend((str(w.get('message', w)) if isinstance(w, dict) else str(w))[:300]
                    for w in result.get('warnings', []))
    warnings.extend(str(w)[:300] for w in result.get('generatedWarnings', []))
    return built, result.get('blocks', []), warnings


def prepare(source, first, last, temp, data_dir, mode, emit):
    if mode not in ('auto', 'off', 'force'):
        raise ValueError('OCR 모드는 auto, off, force 중 하나여야 합니다.')
    emit('progress', stage='analyze', percent=8, message='텍스트 품질과 문서 구조를 분석하고 있어요.')
    native = parse(source, f'{first}-{last}', temp, data_dir)
    needs = {int(p['page']) for p in native.get('pageQuality', []) if p.get('needsOcr')}
    # The PDF extractor also checks empty pages independently of quality heuristics.
    import pymupdf
    with pymupdf.open(source) as doc:
        needs.update(i+1 for i in range(first-1, last) if not doc[i].get_text().strip())
    needs &= set(range(first, last+1))
    if mode == 'off' and needs:
        raise ValueError(f'OCR이 필요한 페이지가 있습니다: {sorted(needs)}. 자동 OCR을 켜 주세요.')
    selected = list(range(first, last+1)) if mode == 'force' else sorted(needs)
    warnings = []
    ocr_pages = {}
    structured = list(native.get('blocks', []))
    for index, number in enumerate(selected):
        emit('progress', stage='ocr', percent=10 + int(25*index/max(1, len(selected))),
             message=f'{number}쪽 글자를 인식하고 있어요. 첫 실행은 모델 다운로드로 시간이 걸릴 수 있어요.')
        result = parse(source, str(number), temp, data_dir, force=True)
        page = next((p for p in result.get('ocrLines', []) if p.get('pageNumber') == number and not p.get('regionsOnly')), None)
        if not page or not any(l.get('text', '').strip() and not l.get('dropped') for l in page.get('lines', [])):
            raise ValueError(f'{number}쪽 OCR에서 글자를 얻지 못했습니다. 모델 다운로드와 원본 상태를 확인해 주세요.')
        ocr_pages[str(number)] = page
        structured = [b for b in structured if b.get('pageNumber') != number]
        structured.extend(result.get('blocks', []))
        warnings.append(f'{number}쪽 OCR 적용: 글자·수식·표·그림 및 배치를 원본과 확인해 주세요.')
    analysis = {'engine': 'kordoc@4.24.54', 'pageQuality': native.get('pageQuality', []),
                'ocrPages': ocr_pages, 'blocks': structured, 'warnings': warnings}
    path = temp / 'analysis.json'
    path.write_text(json.dumps(analysis, ensure_ascii=False), encoding='utf-8')
    return path, warnings
