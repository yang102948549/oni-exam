"""Verify the exact limited first-page conversion experiment, not all-page quality."""
from pathlib import Path
import json,re,zipfile,statistics,xml.etree.ElementTree as E
import pymupdf
out=Path('output/korean_exam_test')
data=json.loads((out/'page01_extraction.json').read_text(encoding='utf-8'))
source=pymupdf.open('국어.pdf');render=pymupdf.open(out/'국어_1페이지_한글렌더.pdf')
chars=[]
for b in render[0].get_text('rawdict')['blocks']:
 if b['type']==0:
  for line in b['lines']:
   for span in line['spans']:
    chars.extend(c for c in span['chars'] if not c['c'].isspace())
text=''.join(c['c'] for c in chars);results=[];cursor=0
for row in data['lines']:
 target=re.sub(r'\s+','',row['text']);idx=text.find(target,cursor)
 if idx<0:idx=text.find(target)
 item={'id':row['id'],'matched_ignoring_whitespace':idx>=0}
 if idx>=0:
  cursor=idx+len(target);cc=chars[idx:cursor]
  box=[min(c['bbox'][0] for c in cc),min(c['bbox'][1] for c in cc),max(c['bbox'][2] for c in cc),max(c['bbox'][3] for c in cc)]
  item.update({'render_bbox':box,'top_error_pt':abs(box[1]-row['bbox'][1]),'left_error_pt':abs(box[0]-row['bbox'][0]),'line_count':len(set(round(c['origin'][1],1) for c in cc))})
 results.append(item)
with zipfile.ZipFile(out/'국어_1페이지_변환시험.hwpx') as z:
 assert z.testzip() is None
 for name in z.namelist():
  if name.endswith(('.xml','.hpf')):E.fromstring(z.read(name))
 ns={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}
 sec=E.fromstring(z.read('Contents/section0.xml'))
 native_text=''.join(t.text or '' for t in sec.findall('.//hp:t',ns))
 native_cells=len(sec.findall('.//hp:tc',ns))
 choices={c:native_text.count(c) for c in '①②③④⑤'}
probe=pymupdf.open(out/'native/edit_probe.pdf');added=None;nextline=None
for b in probe[0].get_text('dict')['blocks']:
 if b['type']==0:
  for line in b['lines']:
   t=''.join(s['text'] for s in line['spans'])
   if t.startswith('편집 안정성'):added=line['bbox']
   if t.startswith('흥미 등의 다양한 요소'):nextline=line['bbox']
overlap=max(0,min(added[3],nextline[3])-max(added[1],nextline[1])) if added and nextline else None
stats={'scope':'Korean PDF page 1 only','source_pages':len(source),'output_pages':len(render),
 'native_text_cells':native_cells,'selected_source_lines':len(results),'matched_lines_ignoring_whitespace':sum(x['matched_ignoring_whitespace'] for x in results),
 'unexpected_wrapped_lines':[x['id'] for x in results if x.get('line_count',1)>1],
 'median_top_error_pt':statistics.median(x['top_error_pt'] for x in results if 'top_error_pt' in x),
 'median_left_error_pt':statistics.median(x['left_error_pt'] for x in results if 'left_error_pt' in x),
 'choice_symbol_counts':choices,'edit_probe_vertical_overlap_pt':overlap,
 'paragraph_reflow_pass':False,'graphics_editable':False,'original_fonts_preserved':False,
 'content_note':'Selected text lines matched ignoring whitespace; image title, excluded occluded text and font fidelity are separate checks.',
 'lines':results}
(out/'validation.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
render[0].get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(out/'render_page_01.png')
report=f'''# 국어 PDF → HWPX 1차 실제 변환 테스트

## 판정

**첫 페이지의 외형을 보존한 편집 가능 시험본 생성은 성공. 자연스러운 문단 편집은 실패.**

전체 40페이지 중 홀수형 첫 페이지(1~3번 문항)만 시험했다. 전체 변환 완료나 범용 변환 성공을 뜻하지 않는다. 기존 자동작성 ZIP은 사용하지 않았다.

## 결과 파일

- [HWPX 시험본](국어_1페이지_변환시험.hwpx)
- [한글에서 출력한 PDF](국어_1페이지_한글렌더.pdf)
- [원본 페이지 이미지](source_page_01.png)
- [변환 결과 이미지](render_page_01.png)
- [문장 추가 후 겹침 증거](edit_probe_crop.png)
- [수치 검사 결과](validation.json)

## 구현과 확인 결과

| 항목 | 결과 |
|---|---|
| 실행 환경 | 한글 2024 COM, 보고 버전 13.0.0.2151 |
| HWPX 열기 | 성공 |
| 한글 PDF 출력 | 성공, {len(render)}페이지 |
| 용지 크기 | 원본과 출력 모두 842 × 1191 pt |
| 선택된 텍스트 줄 | {len(results)}개 |
| 한글 출력에서 텍스트 일치 | {stats['matched_lines_ignoring_whitespace']} / {len(results)}줄, 공백을 제거한 문자열 기준 |
| 편집 가능한 개체 | 테두리 없는 1셀 표 {native_cells}개 |
| 선택지 기호 | {choices} |
| 보정 후 의도하지 않은 줄 꺾임 | {len(stats['unexpected_wrapped_lines'])}개 |
| 텍스트 왼쪽 위치 오차 중앙값 | {stats['median_left_error_pt']:.2f} pt |
| 텍스트 위쪽 위치 오차 중앙값 | {stats['median_top_error_pt']:.2f} pt |
| 문장 추가 시험 | 다음 줄과 세로 약 {overlap:.2f} pt 겹침 |

좌표 오차는 추출된 글자 경계 기준이며 픽셀 유사도나 원본 글꼴 일치를 의미하지 않는다. 문자열 검사는 공백과 시각 서식을 검증하지 않는다.

원본의 텍스트를 제거한 배경 이미지에 테두리·도형·이미지 제목을 남기고, 추출 텍스트를 실제 HWPX 문단이 들어 있는 개별 셀로 올렸다. 페이지 전체를 그림으로 붙인 결과는 아니다. 다만 선·상자·국어영역 이미지 제목은 그림 상태이며 한글 도형이나 텍스트가 아니다.

한글이 직접 만든 표·이미지 개체를 최소 템플릿으로 사용했다. 첫 출력의 2개 줄 꺾임을 확인하고, 한글 PDF에서 측정한 각 줄의 폭과 위치로 장평·위치를 보정했다. 이 보정값은 이 페이지 전용이며 다른 과목에 그대로 적용할 수 없다.

## 발견한 한계

1. **문단 구조가 없다.** 개별 줄이 절대 위치에 고정되어 있다. 글자 수정은 되지만 문장을 늘리면 다음 줄이 밀려나지 않는다.
2. **실제 편집 시험에서 겹침이 재현됐다.** 첫 지문 줄에 “편집 안정성 확인을 위해 문장을 추가합니다.”를 덧붙여 한글에서 출력했다. 추가 줄과 다음 원래 줄이 겹쳤다.
3. **원본 글꼴을 완전히 재현하지 않았다.** 신명조·맑은 고딕으로 대체하고 장평을 맞췄다. 제목 굵기, 선택지 간격, 줄 내부의 강조 상자와 글자 위치 등은 차이가 남는다.
4. **본문 의미 구조를 아직 복원하지 않았다.** 지문·문항·선택지 연결과 공통 지문 묶음은 미구현이다. 화면 순서와 문서 내부 개체 순서도 별개다.
5. 첫 페이지 머리말에서 가려진 이전 홀수형 문구와 중복 쪽번호 2개를 제외했다. 이 필터는 해당 페이지를 눈으로 확인해 적용한 것으로 범용 규칙이 아니다.

## 다음 구현 방향

이 시험본을 외형 비교용 기준으로 보존한다. 다음 버전에서는 줄을 먼저 지문 문단·문항·선택지로 합치고, 문단 내부 줄바꿈과 개체 높이를 한글 조판에 맡겨야 한다. 이후 내용이 늘어날 때 같은 문항의 후속 내용이 함께 이동하는지 검증한다.

첫 페이지의 문단 기반 버전이 편집 시험을 통과한 뒤 2~4페이지의 긴 지문·도표로 확장한다. 40페이지 일괄 처리와 다른 영역의 범용성은 그 다음 검증 대상이다.

## 재실행

작업 폴더에서 Windows Python의 pymupdf와 pywin32, 설치된 한글 2024가 필요하다. 현재 native 폴더의 sample.hwpx와 picture.hwpx는 한글에서 생성한 로컬 시험 자산이다.

```powershell
python scripts/test_korean_hwpx.py
python scripts/render_hwpx_hancom.py output/korean_exam_test/국어_1페이지_변환시험.hwpx --pdf output/korean_exam_test/국어_1페이지_한글렌더.pdf
python scripts/calibrate_korean_hwpx.py
python scripts/test_korean_hwpx.py --calibration output/korean_exam_test/calibration.json
python scripts/render_hwpx_hancom.py output/korean_exam_test/국어_1페이지_변환시험.hwpx --pdf output/korean_exam_test/국어_1페이지_한글렌더.pdf
```

편집 시험용 edit_probe 파일은 최종본과 분리했다. validation.json과 이 보고서는 `scripts/validate_korean_test.py`로 생성했다. 이 검증 스크립트는 사전에 생성한 편집 시험 PDF가 필요하다.
'''
(out/'국어_1차_테스트결과.md').write_text(report,encoding='utf-8')
print(json.dumps({k:v for k,v in stats.items() if k!='lines'},ensure_ascii=False,indent=2))
