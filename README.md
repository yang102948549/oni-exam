# Oni Exam · oni-exam

수능형 2단 시험지 PDF를 편집 가능한 문단 기반 한글(HWPX) 문서로 변환하는 Windows 데스크탑 앱입니다.

## 다운로드

- [전체 릴리스 및 설치 안내](https://github.com/yang102948549/oni-exam/releases)
- [Oni Exam v0.1.0 Windows x64 설치 EXE](https://github.com/yang102948549/oni-exam/releases/download/v0.1.0/Oni-Exam-0.1.0-x64-setup.exe)

설치 파일(`Oni-Exam-0.1.0-x64-setup.exe`)을 내려받아 실행한 뒤 **Oni Exam**을 실행하세요.
(Windows x64, 코드 서명 없음 — SmartScreen 경고 시 `추가 정보 → 실행`)

## 주요 기능

- **PDF → 편집 가능한 HWPX 변환**: 842 × 1191pt 수능형 2단 시험지 PDF에서 문단·지문 상자·표·도형·선지를 추출하여 한글(HWPX) 문서로 조판합니다.
- **독립 실행형 패키징**: Python 런타임과 PyMuPDF 엔진(`oni-engine.exe`)이 설치 패키지에 내장되어 있어 별도의 Python이나 한글 프로그램 설치 없이도 HWPX 파일을 생성할 수 있습니다. (생성된 HWPX 열람·편집에는 한컴오피스 한글 필요)
- **문서 서체 구성**:
  - 본문 (바탕): `KoPub World 바탕체`
  - 제목 · 문항번호 · 숫자 · 기호 (돋움): `KoPub World 돋움체`
  - 수식: `HyhwpEQ`

상세 개발 및 구조 안내는 [`desktop/README.md`](./desktop/README.md)를 참고하세요.
