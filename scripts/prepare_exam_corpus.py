"""Prepare a reproducible exam corpus without altering source uploads.
Usage: python scripts/prepare_exam_corpus.py --year 2026
Requires: pymupdf (PDF inspection only; no conversion is performed).
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pymupdf

LIST_URL = 'https://www.suneung.re.kr/boardCnts/list.do?boardID=1500234&m=0403&s=suneung'
FILE_URL = 'https://www.suneung.re.kr/boardCnts/fileDown.do?fileSeq='
HISTORY_SEQ = '10b6d784275a07a82efa90ddcb8fbd22'
SOCIAL_SEQ = 'a5ffc663f52f11f8dd633837c03ac84a'
SOCIAL_SUBJECTS = ['생활과 윤리','윤리와 사상','한국지리','세계지리','동아시아사','세계사','경제','정치와 법','사회·문화']

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_new_or_equal(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f'Refusing to overwrite differing file: {path}')
    else:
        path.write_bytes(data)

def profile_pdf(path):
    pages = []
    variants = set()
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError(f'Encrypted PDF: {path}')
        for index, page in enumerate(doc):
            text = page.get_text()
            found = [s for s in ['홀수형','짝수형'] if s in text]
            variants.update(found)
            images = page.get_image_info()
            area = page.rect.get_area()
            max_image_area_ratio = max((pymupdf.Rect(x['bbox']).get_area()/area for x in images), default=0)
            # Availability is not a claim that extraction order/coordinates are reliable.
            pages.append({
                'page': index+1,
                'width_pt': round(page.rect.width, 3),
                'height_pt': round(page.rect.height, 3),
                'rotation': page.rotation,
                'text_chars': len(text),
                'replacement_chars': text.count('\ufffd'),
                'image_count': len(images),
                'max_image_area_ratio': round(max_image_area_ratio, 4),
                'drawing_count': len(page.get_drawings()),
                'variants_in_text': found,
                'text_layer_available': bool(text.strip()),
                'text_coordinate_alignment': 'not_tested',
            })
        return {'page_count': len(doc), 'variants_in_text': sorted(variants), 'pages': pages}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--year', type=int, default=2026)
    args=parser.parse_args()
    if args.year != 2026:
        raise ValueError('Download source IDs are verified for 2026 only; verify new source IDs before changing year.')
    root=args.root.resolve()
    base=root/'test_inputs'/f'{args.year}학년도_수능'
    prefix=f'{args.year}학년도_수능'
    archive=base/'원본압축'/f'{prefix}_사회탐구_문제_원본.zip'
    entries=[]
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Archive CRC failure')
        for info in z.infolist():
            if info.is_dir(): continue
            raw_name=info.filename
            name=raw_name
            if not info.flag_bits & 0x800:
                try:name=raw_name.encode('cp437').decode('cp949')
                except UnicodeError:pass
            normalized=name.replace('\\','/')
            if '/' in normalized or '..' in normalized:
                raise ValueError(f'Unexpected archive path: {name}')
            match=re.fullmatch(r'(\d{2}) (.+)_문제\.pdf',name)
            if not match or match.group(2) not in SOCIAL_SUBJECTS:
                raise ValueError(f'Unexpected subject filename: {name}')
            subject=match.group(2)
            token=subject.replace(' ','').replace('·','와')
            path=base/'사회탐구'/f'{prefix}_사회탐구_{token}_문제.pdf'
            data=z.read(info)
            if not data.startswith(b'%PDF-'):raise ValueError(name)
            write_new_or_equal(path,data)
            entries.append({'subject':subject,'area':'사회탐구','path':path,
                'original_filename':name,'source_url':FILE_URL+SOCIAL_SEQ,
                'source_archive':str(archive.relative_to(root)), 'sha256':digest(data)})
    if len(entries)!=9:
        raise ValueError(f'Expected 9 social subjects, got {len(entries)}')
    history=base/'한국사'/f'{prefix}_한국사_문제.pdf'
    entries.append({'subject':'한국사','area':'한국사','path':history,
        'original_filename':'한국사영역_문제지.pdf','source_url':FILE_URL+HISTORY_SEQ,
        'source_archive':None,'sha256':digest(history.read_bytes())})
    for subject in ['국어','영어']:
        source=root/f'{subject}.pdf'
        if not source.exists():continue
        path=base/subject/f'{prefix}_{subject}_문제.pdf'
        write_new_or_equal(path,source.read_bytes())
        entries.append({'subject':subject,'area':subject,'path':path,
            'original_filename':source.name,'source_url':None,'source_archive':None,
            'source_local_path':str(source.relative_to(root)), 'sha256':digest(source.read_bytes())})
    order=['국어','영어','한국사']+SOCIAL_SUBJECTS
    entries.sort(key=lambda row:order.index(row['subject']))
    for item in entries:
        path=item['path']
        item.update(profile_pdf(path))
        item['path']=path.relative_to(root).as_posix()
        item['bytes']=path.stat().st_size
        item['conversion_status']='not_started'
        print(item['subject'],item['page_count'],'pages',item['variants_in_text'],flush=True)
    manifest={'schema_version':1,'academic_year':args.year,'exam':'대학수학능력시험',
        'prepared_at':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        'source_listing':LIST_URL,'archive_sha256':digest(archive.read_bytes()),
        'notes':['원본 업로드 보존; 정리본은 바이트 동일 복사',
                 '텍스트 계층 존재는 추출 내용·좌표 정확성을 보증하지 않음',
                 '유형은 텍스트에서 관찰한 값이며 페이지 렌더 대조는 후속 검증',
                 'HWPX 변환은 아직 수행하지 않음'], 'documents':entries}
    (base/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    configs=[]
    for item in entries:
        configs.append({'subject':item['subject'],'area':item['area'],'input_pdf':item['path'],
            'page_range':None,'paper_size':'from_pdf','columns':'detect_per_page',
            'reading_order':'detect_columns_then_blocks','ocr_policy':'only_when_needed',
            'text_coordinate_alignment_check':True,'preserve_original_text':True,
            'figure_policy':'preserve_source_region','equation_policy':'editable_when_supported',
            'choice_layout':'detect','passage_question_linking':True,
            'output_mode':'editable_with_layout_preservation','template_hwpx':None,
            'render_engine':'hancom','status':'configuration_only_not_executed'})
    (base/'conversion_cases.json').write_text(json.dumps({'schema_version':1,
        'note':'후속 변환기 입력 설계용 설정. 이 파일만으로 변환되지는 않음.',
        'cases':configs},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 2026학년도 수능 PDF 변환 테스트 자료','',
        '한국사 및 사회탐구 문제를 평가원 공식 자료실에서 내려받았다. 사회탐구 ZIP은 CRC 검사 후 과목별 PDF로 압축 해제했다. 국어·영어는 사용자 업로드를 변경 없이 복사했다.','',
        f'- [공식 자료실]({LIST_URL})',
        '- 원본 ZIP: `원본압축/2026학년도_수능_사회탐구_문제_원본.zip`',
        '- 파일명: `2026학년도_수능_[영역]_[과목]_문제.pdf` (영역과 과목이 같으면 한 번만 표기)',
        '- `manifest.json`: 원본 파일명, 다운로드 주소, SHA-256, 페이지별 크기·텍스트·이미지·도형 통계',
        '- `conversion_cases.json`: 과목별 변환 변수 초안. 변환 실행 결과가 아님.',
        '- 수학·과학탐구·직업탐구·제2외국어는 이번 수집 대상에 포함하지 않았다.','',
        '| 영역 | 과목 | 페이지 | 텍스트에서 관찰한 유형 | 파일 |','|---|---|---:|---|---|']
    for row in entries:
        rel=Path(row['path']).relative_to(base.relative_to(root)).as_posix()
        lines.append(f"| {row['area']} | {row['subject']} | {row['page_count']} | {', '.join(row['variants_in_text']) or '유형 표기 미확인'} | [{Path(rel).name}]({rel}) |")
    lines += ['', '## 다음 검증', '',
        '국어부터 텍스트 좌표와 실제 렌더 위치를 대조한 뒤, 지문·문항·선택지 복원 및 HWPX 생성을 테스트한다. 한국사·사회탐구에서는 사진·지도·도표·표와 본문의 결합도 추가 검증한다.',
        '한글 자동작성 ZIP은 이 자료 준비 및 후속 변환 경로의 입력으로 사용하지 않는다.',
        '',f"총 {len(entries)}개 PDF, {sum(r['page_count'] for r in entries)}페이지. PDF 열기 및 ZIP CRC 검사 완료. HWPX 생성과 시각 대조는 미실행."]
    (base/'자료목록.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('TOTAL',len(entries),sum(x['page_count'] for x in entries))
if __name__=='__main__':main()
