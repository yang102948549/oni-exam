# Claude · HWPX · PDF GitHub 조사 — 수능·모의고사 변환 스킬 설계

- 조사일: 2026-10-10 (Asia/Seoul)
- 목적: 대한민국 수능·모의고사 PDF를 원본과 유사하면서도 편집 가능한 HWPX로 재구성하는 스킬의 기반 조사
- 단계: GitHub 공개 README, SKILL.md, 일부 소스 코드 검토. 설치·변환 실행·성능 실측은 하지 않았다.
- 이 문서는 조사 및 설계 초안이다. 실행 가능한 변환 스킬이나 검증 완료된 제품이 아니다.
- 링크는 조회 시점의 가변 브랜치이다. 구현 채택 시 커밋 SHA·패키지 버전·모델 버전을 고정해야 한다.

## 목차

1. 조사 결론
2. 검색 범위와 근거 수준
3. Claude/HWPX 스킬 후보
4. PDF 분석 및 HWPX 기반 도구
5. 소스 코드에서 확인한 한계
6. 추천 구성과 중간 데이터
7. SKILL.md 설계 초안
8. 비교 평가 계획
9. 도입 전 확인 사항과 다음 작업

## 1. 조사 결론

찾은 저장소들은 크게 PDF 분석, HWPX 생성·편집, 한글 프로그램 자동화, 에이전트 스킬로 나뉜다. 이들을 연결할 재료는 있지만, 이번 확인 범위에서는 수능 PDF를 입력받아 편집 가능한 수식과 원본 배치를 함께 보존하는 완성형 변환기의 검증된 근거를 찾지 못했다. 검색 결과가 없다는 이유로 그러한 프로젝트가 존재하지 않는다고 단정하지는 않는다.

초기 구현은 다음 조합으로 실험하는 것이 타당하다. 이는 조사에 따른 설계 제안이며 성능 순위가 아니다.

- PDF 좌표·문자·선 분석: pdfplumber.
- 복잡한 문서 구조와 OCR 비교 후보: Docling, MinerU, Marker.
- HWPX 작성 엔진: python-hwpx 및 python-hwpx-automation.
- 수식·2단 시험지 생성 참고: hohyon-ryu/claude-hwpx-plugin.
- 스킬 워크플로 참고: airmang/hwpx-plugins, jkf87/hwpx-skill.
- 실제 한글 렌더링·편집 검증: Windows 한글 COM / pyhwpx 또는 해당 자동화 계층의 한컴 렌더 경로.

핵심 개발 대상은 문항·지문·선택지 관계를 복원하는 시험지 전용 중간 표현과, 그것을 안정적으로 HWPX에 배치하는 조판 계층이다. Markdown만 중간 형식으로 쓰면 좌표·단 경계·문항 묶음·원본 근거를 충분히 보존하기 어렵다.

## 2. 검색 범위와 근거 수준

웹 검색에서 GitHub 도메인을 지정하고 저장소 원문을 열어 확인했다. GitHub 전체 코드 검색이나 모든 브랜치를 조사한 것은 아니다.

대표 검색어:

- `site:github.com Claude HWPX skill PDF`
- `site:github.com hwpx pdf converter claude`
- `site:github.com "PDF to HWPX"`
- `site:github.com "PDF" "HWPX" "수능"`
- `site:github.com "python-hwpx"`
- `site:github.com anthropics skills pdf SKILL.md`

근거 구분:

| 표시 | 의미 |
|---|---|
| 문서 확인 | 유지보수자가 README 또는 SKILL.md에 설명한 범위. 실측 보증 아님 |
| 코드 확인 | 특정 소스에서 실제 구현 방식 확인. 전체 기능 검증 아님 |
| 설계 판단 | 이번 프로젝트에 적용할 때의 추론 또는 제안 |
| 미확인 | 실행·라이선스 전문·한컴 출력 등 추가 검증 필요 |

특히 `HWP → HWPX`, `HWPX → PDF`, `PDF → Markdown`, `PDF → HWPX`는 별개 기능이다. 검색 결과에 PDF와 HWPX가 함께 나오는 것만으로 마지막 경로를 지원한다고 판단하지 않았다.

## 3. Claude/HWPX 스킬 후보

### 3.1 hohyon-ryu/claude-hwpx-plugin — 시험지·수식 참고 우선순위 높음

- [저장소](https://github.com/hohyon-ryu/claude-hwpx-plugin)
- [SKILL.md](https://github.com/hohyon-ryu/claude-hwpx-plugin/blob/main/skills/hwpx/SKILL.md)
- [generator.py](https://github.com/hohyon-ryu/claude-hwpx-plugin/blob/main/scripts/generator.py)

문서 확인: HWPX 읽기·쓰기, Markdown 변환, 수식, 표, 다단 구성과 B4 2단 시험지 템플릿을 소개한다. README는 MIT로 표시한다.

활용 후보: 한글 수식 스크립트 매핑, HWPX 구성 요소, 시험지 템플릿 구성 방식.

한계: 소개된 주요 입력 경로는 Markdown/텍스트 또는 HWP/HWPX이다. PDF 문항 분석과 원본 지면 복원까지 제공한다는 근거는 확인하지 못했다. 생성기에서 발견한 크기 추정 방식은 5절에 정리했다. 템플릿의 실제 한컴 호환성은 실행 검증이 필요하다.

### 3.2 airmang/hwpx-plugins — 스킬·엔진 역할 분리 참고

- [저장소](https://github.com/airmang/hwpx-plugins)
- [SKILL.md](https://github.com/airmang/hwpx-plugins/blob/main/SKILL.md)

문서 확인: python-hwpx 프로젝트가 유지보수하는 스킬 번들이다. HWPX 엔진, 자동화 계층, 에이전트 지침을 별도 저장소로 구분한다. README는 Apache-2.0을 표시한다.

활용 후보: 스킬에는 작업 선택과 품질 판단을 두고 반복적인 XML 처리는 코드에 맡기는 구성. 한컴 렌더 검증과 순수 Python 편집을 구별하는 방식.

한계: 프로젝트의 first-party라는 의미이며 한컴 공식 스킬이라는 뜻은 아니다. PDF 시험지 복원 성능은 별도 검증해야 한다.

### 3.3 jkf87/hwpx-skill — 생성·템플릿·렌더 검증 워크플로

- [저장소](https://github.com/jkf87/hwpx-skill)
- [SKILL.md](https://github.com/jkf87/hwpx-skill/blob/main/SKILL.md)

문서 확인: Markdown/텍스트에서 HWPX 생성, 템플릿 치환, 기존 문서 편집, HWP 변환, 문제지·답안지 생성 등을 설명한다. JSON 명세 기반 생성 및 실제 한컴 PDF/PNG 검사 경로도 소개한다.

활용 후보: 원고와 조판 설정의 분리, 생성 결과 보고서, 정적 검증과 시각 검증의 구분.

한계: 문제지 신규 생성은 기존 PDF 시험지를 역복원하는 것과 다르다. 서식 보존에 대한 README 표현을 모든 입력에 대한 보증으로 사용하지 않는다. 재사용 라이선스 전문은 추가 확인 대상이다.

### 3.4 divisonofficer/hwpx_skill — 기존 HWPX 편집·검증 참고

- [저장소](https://github.com/divisonofficer/hwpx_skill)
- [SKILL.md](https://github.com/divisonofficer/hwpx_skill/blob/main/SKILL.md)

문서 확인: 패키지·XML·참조 검증, 문서 구조 지도, 플레이스홀더 치환, 표 셀 편집, 의미 차이 보고를 제공한다고 설명한다. 지원 표에서 PDF는 별도 PDF 스킬 영역으로 제외한다. README는 MIT로 표시한다.

활용 후보: 원본 복사 후 편집, 생성 전후 구조 비교, 깨진 참조 검출.

한계: 신규 문서 생성은 제한적이라고 명시되어 있다. page-guard 같은 휴리스틱은 실제 한글 렌더링 결과와 동등하지 않다.

### 3.5 Engccer/hwpx-automation — 변환 방향과 환경 분기 참고

- [저장소](https://github.com/Engccer/hwpx-automation)

문서 확인: HWP/HWPX 편집, HWP→HWPX, Markdown/PDF 출력. HWP 변환에는 JDK 21, PDF 출력에는 Windows·한컴·pywin32가 필요하다고 설명한다.

활용 후보: 순수 Python 처리와 한컴 종속 처리의 명확한 분기.

한계: PDF 출력 기능은 PDF 입력 복원 기능이 아니다. 라이선스 전문과 실제 변환 손실은 미확인이다.

### 3.6 imsebeom 계열 — 호환성 문제와 검증 사례 참고

- [hwpx-skills](https://github.com/imsebeom/hwpx-skills)
- [hwpx2의 SKILL.md](https://github.com/imsebeom/hwpx2/blob/main/SKILL.md)
- [hwpx](https://github.com/imsebeom/hwpx)

문서 확인: 경량 HWPX 생성·편집, 글꼴 확인, 템플릿 처리, 렌더링 검사 등의 사례가 있다. hwpx-skills는 MIT를 표시한다. 각 저장소의 범위와 의존성은 같다고 가정하지 않는다.

활용 후보: 스타일 참조, 표 속성, 단위, 줄 배치 캐시 등 실제 렌더링에 영향을 줄 수 있는 항목의 재현 테스트 목록.

한계: 커뮤니티가 제시한 호환성 규칙은 대상 한글 버전과 예제 파일로 재검증해야 한다. 특히 파일 용량 감소율은 압축·이미지 인코딩 등의 영향도 받으므로 콘텐츠 손실률로 해석하면 안 된다.

### 3.7 anthropics/skills — Claude 스킬 구조 참고

- [저장소](https://github.com/anthropics/skills)
- [PDF SKILL.md](https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md)
- [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)

문서 확인: SKILL.md와 스크립트·참고자료를 결합하는 구조를 제시한다. PDF 스킬은 추출, 병합, 분할, OCR, 폼 등 일반 PDF 처리를 다룬다.

활용 후보: 작업 트리거를 좁게 정의하고, 도구별 상세 절차를 별도 참조로 분리하는 구성.

한계: HWPX 변환 스킬은 아니다. 저장소 전체를 동일한 라이선스로 보면 안 된다. README는 문서 스킬을 source-available로 구분하고 PDF SKILL.md는 Proprietary 및 개별 LICENSE.txt를 명시한다. 원문을 통째로 복제하기보다 자체 지침을 작성한다.

## 4. PDF 분석 및 HWPX 기반 도구

| 저장소 | 문서상 역할 | 이번 프로젝트의 활용 후보 | 남는 과제 |
|---|---|---|---|
| [airmang/python-hwpx](https://github.com/airmang/python-hwpx) | 한컴 없이 HWPX 읽기·편집·생성 | HWPX 작성 엔진 | PDF 인식·시험지 배치 별도 |
| [airmang/python-hwpx-automation](https://github.com/airmang/python-hwpx-automation) | 저작·양식·시험지 워크플로, CLI, 선택형 MCP | 중간 데이터에서 문서 생성, 한컴 렌더 연결 | 실제 API와 시험지 표현력 검증 |
| [martiniifun/pyhwpx](https://github.com/martiniifun/pyhwpx) | pywin32 기반 한글 자동화 | 한글에서 열기·저장·편집 검사 | Windows 및 한글 설치 필요 |
| [hancom-io/hwpx-owpml-model](https://github.com/hancom-io/hwpx-owpml-model) | OWPML 파일 필터 모델 | XML 요소 구조 교차 확인 | 고수준 PDF 복원기 아님 |
| [neolord0/hwpxlib](https://github.com/neolord0/hwpxlib) | Java HWPX 라이브러리 | 별도 작성 엔진 비교·구조 참고 | Java 의존성, 조판 검증 필요 |
| [jsvine/pdfplumber](https://github.com/jsvine/pdfplumber) | 문자·선·사각형·표 추출과 시각 디버깅 | 디지털 PDF의 좌표와 경계 분석 | 스캔 OCR·한글 수식 생성 별도 |
| [docling-project/docling](https://github.com/docling-project/docling) | 레이아웃·읽기 순서·표·수식 등 문서 분석 | 구조 추출 비교 후보 | HWPX 작성 및 시험지 관계 모델 별도 |
| [opendatalab/MinerU](https://github.com/opendatalab/MinerU) | PDF 등의 구조화·OCR·문서 처리 | 스캔·복잡한 수식 페이지 비교 후보 | 선택 모드별 자원·라이선스·품질 확인 |
| [datalab-to/marker](https://github.com/datalab-to/marker) | 문서를 Markdown·JSON·HTML 등으로 변환 | 수식·표·이미지 추출 비교 후보 | 시험지 조판 및 정보 보존 설정 별도 |

pdfplumber는 디지털 생성 PDF에 더 적합하다고 스스로 설명한다. 모든 페이지를 OCR로 재인식하기보다 페이지·영역별로 텍스트 계층의 품질을 먼저 확인하는 구성이 합리적이다.

python-hwpx-automation의 PDF 입력을 Markdown으로 읽는 기능과 시험지 저작 기능이 각각 존재하더라도, 그 둘을 이어 붙인 결과의 원본 재현성이 입증되는 것은 아니다. 또한 README에서 배포 승인 후보와 실제 공개 버전을 구분하므로 설치 버전을 문서 예제 하나만 보고 결정하지 않는다.

Marker는 머리말·꼬리말 등의 제거를 기능으로 소개한다. 시험지에서는 과목명·쪽 번호·시험지 식별 정보가 필요한 내용일 수 있으므로 보존 설정과 중간 결과를 확인해야 한다. 라이브러리 기본값이 프로젝트 요구사항에 맞는지 검증한다.

## 5. 소스 코드에서 확인한 한계

대상: [claude-hwpx-plugin의 generator.py](https://github.com/hohyon-ryu/claude-hwpx-plugin/blob/main/scripts/generator.py). 아래는 조회한 코드의 일부에 대한 관찰이며 실행 실패 보고는 아니다.

| 코드 관찰 | 시험지에 적용할 때의 설계 판단 |
|---|---|
| 수식 폭을 스크립트 문자열 길이 × 600으로 추정하고 상한을 둠 | 중첩 분수·행렬 등의 실제 폭과 일치하지 않을 수 있어 렌더 후 크기 검사 필요 |
| 수식 개체 높이에 3000 사용 | 큰 분수·다중행 수식의 높이·기준선 테스트 필요 |
| 표 전체 폭 42000, 행 높이 1800 지정 | 2단 안의 표·여러 줄 셀 내용에 맞춘 폭과 높이 계산 필요 |
| B4 설정을 기존 XML의 특정 숫자 문자열 치환으로 처리 | 다른 템플릿 값에 적용되는지 확인하고 구조 기반 설정 고려 |
| 본문을 줄별로 처리하고 빈 줄을 건너뜀 | 원본 여백·문항 그룹·단 나눔은 별도 데이터로 유지해야 함 |

이 코드는 HWPX 작성 예제로 참고할 수 있지만, 원본 PDF의 좌표나 문항 관계를 자동 복원하는 기능으로 확대 해석하면 안 된다.

추가로 [hwpx2의 SKILL.md](https://github.com/imsebeom/hwpx2/blob/main/SKILL.md)는 특정 HWP 변환 경로의 테두리·서식 문제와 정적 검증의 한계를 기록한다. 해당 사례는 HWP→HWPX에 관한 것으로 PDF→HWPX 실패의 직접 증거로 인용하지 않는다.

## 6. 추천 구성과 중간 데이터

### 6.1 처리 단계 — 자체 설계 제안

```text
PDF
 ├─ 페이지 크기·회전·텍스트 계층 확인
 ├─ 글자/선/이미지/영역 좌표 추출
 └─ 필요한 영역만 OCR·수식 인식
        ↓
시험지 중간 데이터
 지문 / 문항 / 조건 / 선택지 / 수식 / 표 / 그림 / 단 / 쪽
        ↓
검토된 시험지 템플릿 + HWPX 작성 엔진
        ↓
구조 검사 → 한글 렌더 → 원본 비교 → 편집 안정성 검사
        ↓
HWPX + 비교 미리보기 + 미확인 항목 보고서
```

원본과 같은 페이지 배치와 편집 후 자연스러운 재배치가 충돌할 때에는 두 결과를 구분해 평가한다. 페이지를 통째로 그림으로 넣는 방식은 외형 기준선으로만 사용하고, 편집 가능한 변환 성공으로 계산하지 않는다.

### 6.2 중간 데이터에 필요한 정보

| 묶음 | 주요 필드 | 목적 |
|---|---|---|
| 원본 | 파일 해시, 페이지 번호, 페이지 크기·회전 | 결과 추적과 재현 |
| 영역 | 영역 ID, bbox, 좌표 원점·단위, column_id, reading_order | 좌표계 혼동과 단 순서 오류 방지 |
| 문항 | question_id, passage_id, block_ids, 배점 | 지문·문항·선택지 연결 |
| 본문 | 원문 텍스트, 스타일 구간, 출처 영역 | 내용과 서식 분리 |
| 수식 | 원본 crop, 인식 표현, 한글 스크립트, 지원 여부, 검토 상태 | 인식과 수식 변환을 별도 검증 |
| 도표 | 원본 영역, 자산 파일, 캡션·라벨 관계 | 그림과 문항의 결합 유지 |
| 조판 | 용지 크기, 여백, 단 간격, 문항 묶음 규칙 | 원본 지면 재구성 |
| 검증 | 내용·구조·시각·편집 상태, 미지원 목록 | 겉보기 성공 방지 |

OCR 신뢰도는 엔진이 제공할 때 기록한다. 모델이 임의로 만든 숫자를 객관적인 신뢰도로 취급하지 않는다. 원본 좌표를 HWPX의 흐름 기반 배치에 그대로 복사하는 것만으로 편집 안정성을 얻을 수는 없다.

수식은 LaTeX 문자열의 전역 치환만으로 처리하기보다, 지원 범위를 정한 구조 변환기를 마련한다. 중첩 분수·근호·행렬·조건부 식·벡터·단위·첨자를 각각 검증한다. 미지원 수식은 원본 이미지를 보존하고, 편집 불가 상태를 보고서에 명시한다.

## 7. SKILL.md 설계 초안

아래는 자체 작성한 방향 제안이다. 실제 스크립트와 템플릿 구현 후 정식 SKILL.md로 분리한다. 아직 없는 명령을 실행 가능한 기능으로 안내하지 않는다.

```yaml
---
name: korean-exam-pdf-to-hwpx
description: 대한민국 수능·모의고사 PDF를 분석해 본문과 수식을 편집할 수 있는 HWPX 시험지로 재구성하고, 원본 배치와 한글 렌더링 결과를 비교한다. PDF 시험지의 한글 변환·양식 복원 요청에 사용한다.
---
```

본문에 포함할 핵심 지침:

1. 입력 PDF의 디지털/스캔/혼합 상태, 용지 크기, 단 구성을 확인한다. B4·2단을 모든 입력에 강제하지 않는다.
2. 추출 결과를 원본 페이지·영역과 연결한다. 지문·문항·선택지·수식을 임의로 요약하거나 고치지 않는다.
3. 본문은 문단, 수식은 가능한 범위에서 한글 수식 개체로 작성한다. 이미지 대체가 발생하면 항목별로 표시한다.
4. 그림은 원본 자산 또는 적절한 해상도의 영역 이미지로 보존한다. 그래프를 추정해 다시 그리지 않는다.
5. 검증된 템플릿의 스타일과 단 설정을 사용한다. 눈에 보이는 정렬을 공백 반복만으로 맞추지 않는다.
6. 패키지·XML·참조 검증과 실제 한글 렌더 검증을 구분한다. 한글 렌더를 수행하지 못했으면 시각 검증 완료라고 보고하지 않는다.
7. 문제 번호, 선택지 수, 수식 기호, 도표 라벨 등 내용 검사를 먼저 수행하고 지면 오차를 확인한다.
8. 수정 후 줄바꿈·개체 이동을 표본 검사한다. 결과 HWPX와 함께 미지원·불확실 항목을 제공한다.

후속 구현 시 필요한 파일 구성 예시 — 아래 파일들은 아직 생성하지 않았다:

```text
korean-exam-pdf-to-hwpx/
├── SKILL.md
├── references/
│   ├── github-research.md
│   ├── exam-ir.md
│   ├── equation-mapping.md
│   └── validation.md
├── scripts/
│   ├── inspect_pdf.py
│   ├── extract_exam.py
│   ├── build_hwpx.py
│   └── compare_render.py
└── assets/
    └── 검증된 시험지 템플릿.hwpx
```

스킬 지침은 도구 선택·원문 보존·실패 처리에 집중하고, 단위 변환·XML 생성·수식 변환은 테스트 가능한 코드에 둔다.

## 8. 비교 평가 계획

### 8.1 초기 표본 제안

- 국어: 긴 공통 지문, 보기 상자, 여러 문항 연결.
- 수학: 본문 속 수식, 중첩 분수, 함수 그래프, 짧은 선택지와 긴 선택지.
- 영어: 긴 지문, 밑줄·빈칸, 문장 삽입 위치.
- 탐구: 복합 표·그래프, ㄱ·ㄴ·ㄷ 보기, 작은 기호.
- 같은 내용의 디지털 PDF와 스캔 PDF를 포함해 OCR 영향 분리.

처음에는 과목별 특징 페이지 2~3장으로 실패 유형을 파악하고, 이후 전체 시험지의 쪽 흐름을 평가한다. 이미지 기반 외형 복사 결과도 기준선으로 만들되 편집 점수는 별도 처리한다.

### 8.2 평가 항목

| 항목 | 관찰·측정 방식 |
|---|---|
| 내용 보존 | 원문 대조: 누락 문자·선택지·수식·도표 라벨 수 |
| 수식 정확성 | 수식 구조와 기호 대조, 한글 수식 편집기에서 개체 열기 |
| 문항 구조 | 읽기 순서, 지문 연결, 문항·선택지 묶음 정확성 |
| 지면 유사도 | 동일 크기로 렌더 후 오버레이, 기준점·줄바꿈·쪽 수 비교 |
| 편집 안정성 | 본문 문장 추가, 수식 수정, 문항 이동 후 겹침·잘림 검사 |
| 실용성 | 페이지당 수동 보정 시간, 처리 시간, 최대 메모리 |

픽셀 차이는 글꼴 렌더링과 안티앨리어싱에도 민감하다. 픽셀 지표 하나만으로 내용·편집 품질을 판정하지 않는다. 자동 지표의 임계값은 실제 표본을 본 뒤 정한다.

최소 납품 조건 제안: 한글에서 열림, 원문 핵심 내용 누락 없음, 의도하지 않은 개체 겹침·잘림 없음, 이미지 대체 수식과 미검증 항목 공개. 아직 이러한 조건을 통과한 산출물은 없다.

## 9. 도입 전 확인 사항과 다음 작업

### 9.1 코드·모델·템플릿의 재사용 조건

- pdfplumber와 Docling은 저장소에서 MIT로 표시한다. Docling 모델은 개별 조건을 확인하도록 안내한다.
- Marker는 코드와 모델 가중치 조건을 구분한다. 코드의 Apache-2.0 표시를 모델 조건으로 확대하지 않는다.
- MinerU의 조회 시점 README는 Apache 2.0 기반 추가 조건이 있는 별도 라이선스를 안내한다. 과거 버전의 라이선스 설명을 그대로 적용하지 않는다.
- Anthropic PDF 스킬은 별도 LICENSE.txt를 확인해야 하며, 공개 열람 가능과 자유 재배포 가능을 동일시하지 않는다.
- 나머지 저장소도 실제 사용할 커밋의 LICENSE, NOTICE, 템플릿·글꼴 조건을 확인한 뒤 재사용한다.

근거: [pdfplumber](https://github.com/jsvine/pdfplumber), [Docling](https://github.com/docling-project/docling#license), [Marker](https://github.com/datalab-to/marker#commercial-usage), [MinerU](https://github.com/opendatalab/MinerU#license-information), [Anthropic skills](https://github.com/anthropics/skills#about-this-repository).

### 9.2 다음 구현 순서

1. 작업 폴더에 이미 있는 `new-hwpx-master-v5-1-20260720_압축해제필요.zip`의 지침·코드·템플릿을 조사한다. 이번 작업에서는 존재만 확인했으며 압축 해제·수정하지 않았다.
2. 원본 시험지 PDF와 가능하면 대응 HWPX를 준비해 비교 기준을 만든다.
3. 검증된 HWPX 템플릿과 최소 수식·문단 생성 경로부터 시험한다.
4. 같은 페이지에서 PDF 추출 후보를 비교하고 시험지 중간 데이터 규격을 확정한다.
5. 한글 렌더 비교와 편집 시험을 통과한 경로만 정식 스킬 명령으로 연결한다.

이 조사에서는 저장소 설치·사용자 설정 변경·외부 서비스 업로드를 수행하지 않았다. 생성한 산출물은 이 Markdown 조사 문서이며, 성능 순위와 완전 변환 보장은 아직 제시할 수 없다.
