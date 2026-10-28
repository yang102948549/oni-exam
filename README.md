# Oni Exam · oni-exam

수능형 2단 시험지 PDF를 편집 가능한 문단 기반 한글(HWPX) 문서로 변환하는 Windows 데스크탑 앱입니다.

## 다운로드

- [전체 릴리스 및 설치 안내](https://github.com/yang102948549/oni-exam/releases)
- [Oni Exam v0.2.0 Windows x64 설치 EXE](https://github.com/yang102948549/oni-exam/releases/download/v0.2.0/Oni-Exam-0.2.0-x64-setup.exe)

설치 파일(`Oni-Exam-0.2.0-x64-setup.exe`)을 내려받아 실행한 뒤 **Oni Exam**을 실행하세요.
(Windows x64, 코드 서명 없음 — SmartScreen 경고 시 `추가 정보 → 실행`)

## 주요 기능

- **PDF → 편집 가능한 HWPX 변환**: 842 × 1191pt 수능형 2단 시험지 PDF에서 문단·지문 상자·표·도형·선지를 추출하여 한글(HWPX) 문서로 조판합니다.
- **독립 실행형 패키징**: Python 런타임과 PyMuPDF 엔진(`oni-engine.exe`)이 설치 패키지에 내장되어 있어 별도의 Python이나 한글 프로그램 설치 없이도 HWPX 파일을 생성할 수 있습니다. (생성된 HWPX 열람·편집에는 한컴오피스 한글 필요)
- **프로그램 내 자동 업데이트**: 앱 실행 시 및 `환경 설정 → 프로그램 업데이트`에서 GitHub Releases의 최신 버전을 확인하고 앱 안에서 바로 다운로드·설치할 수 있습니다.
- **문서 서체 구성 (앱 내장 및 자동 설치)**:
  - 문제 본문 글씨: `신명 중명조` (10.91pt ~ 11.5pt, 장평 95%, 자간 -5%)
  - 표 · 일러스트 폰트: `문체부 돋음체` (11.5pt, 장평 95%, 자간 -5%)
  - 문항 번호 / 제2교시 등 제목: `한양견명조`
  - 5지선다형 / 단답형 번호: `신명 태고딕`
  - 수식 및 숫자: `HyhwpEQ` 계열 수식 폰트

상세 개발 및 구조 안내는 [`desktop/README.md`](./desktop/README.md)를 참고하세요.
