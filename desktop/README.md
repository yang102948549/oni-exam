# Oni Exam · Windows 데스크탑 앱

Oni School 스타일을 사용하는 Tauri 2 + React + Python PDF→HWPX 작업실입니다.

## 사용

1. Windows 설치 파일을 실행하거나 빌드된 앱을 엽니다.
2. PDF를 드래그하거나 `Ctrl+O`로 선택합니다.
3. 제목·과목·페이지 범위·저장 폴더를 정하고 **한글 문제지 만들기**를 누릅니다.
4. **한글에서 열기**로 결과를 검토합니다. 기존 파일을 덮어쓰지 않도록 결과 이름에 시각과 식별자를 붙입니다.

HWPX 생성에는 한글과 별도 Python 설치가 필요하지 않습니다. HWPX 편집 및 최종 배치 확인에는 한글 또는 호환 편집기가 필요합니다. Python과 PyMuPDF는 설치 패키지에 포함됩니다. UI 글꼴도 로컬에 포함되어 네트워크를 사용하지 않습니다.

## 현재 지원 범위

- 텍스트를 포함하는 842 × 1191pt 수능형 2단 PDF.
- 국어·영어 및 수학·한국사·탐구 과목 설정. 수식·도형 분석은 실험 기능입니다.
- 원본 페이지 미리보기, 범위 선택, 편집 가능한 HWPX 생성, 작업 기록 검색, 파일/폴더 열기.
- 스캔 OCR, 다른 판형 자동 분석, HWPX 결과 자체의 앱 내 렌더링은 포함하지 않습니다.
- 기존 추출·조판 엔진을 연결했습니다. 모든 문항의 인식 정확도나 원본과 같은 지면을 보장하지 않습니다. 배포 패키지는 코드 서명하지 않은 테스트 빌드입니다.

## 저장

파일은 사용자가 고른 로컬 폴더에 저장합니다. 기록과 기본 폴더 설정은 Tauri의 앱 데이터 디렉터리(`net.onischool.exam`) 아래 `workspace.sqlite3`에 저장합니다. 원본 파일을 업로드하거나 복사하지 않습니다. 임시 추출 데이터는 작업 후 제거합니다. 앱 실행 중 변환은 하나씩 처리하며, 변환 중 창 닫기는 완료까지 보류합니다.

## 개발

Windows, Node.js, Rust MSVC 도구체인, C++ Build Tools, WebView2, Python 3.11 이상이 필요합니다.

```powershell
cd desktop
npm ci
python -m pip install -r engine/requirements.txt
npm run engine:build
npm run desktop:dev
```

개발 시 `ONI_PYTHON` 환경 변수로 Python 실행 경로를 지정할 수 있습니다. `npm run dev`는 화면 확인용 웹 모드이며 파일 변환은 Tauri 앱에서만 동작합니다.

```powershell
npm run test:engine
npm run build
cd src-tauri
cargo check --locked
cd ..
npm run desktop:build
```

설치 파일: `src-tauri/target/release/bundle/nsis/`. 엔진은 `src-tauri/binaries/oni-engine-x86_64-pc-windows-msvc.exe`로 생성되어 설치 시 앱 옆에 `oni-engine.exe`로 배치됩니다. 빌드에는 원본 시험지 PDF를 포함하지 않습니다.

## 구조

- `src/`: Oni 디자인 토큰, React 화면, Tauri IPC 연결.
- `src-tauri/`: Windows 창·파일 선택·엔진 호출·진행 이벤트·문서 열기.
- `engine/worker.py`: JSON 입출력, PDF 검사/미리보기, 기존 스크립트 실행, SQLite 기록, 결과 XML 검사.
- `scripts/build_engine.py`: 필요한 스크립트와 템플릿만 포함하는 PyInstaller 패키징.
- `../scripts/extract_items4.py`, `../scripts/build_hwpx_doc4.py`: 실제 추출·조판 엔진.

## 디자인 출처

[Oni School Components](https://www.figma.com/design/AzTquoRRmIlNmzHU7lNXUX?node-id=0-1)와 [onischool.net](https://onischool.net)을 참고했습니다.

- 색상 `6:38`: canvas `#FAFAF9`, surface `#FFFFFF`, subtle `#F3F3F1`, primary `#292927`, muted `#71716B`, border `#DCDCD6`, action `#1B70C9`, focus `#2383E2`.
- 타이포그래피 `6:73`: Noto Sans KR. 앱의 UI 글꼴이며 문제지 서체와 구분합니다.
- 버튼 `7:42`: 36px, 반경 6px. 입력 `7:245`: 레이블 유지, 40px 입력 컨트롤.
- 브랜드 `57:59`: 미배정 인디고 `#5865C8`의 원본 SVG를 로컬 저장했습니다. 헤더의 22×22px 아이콘은 원본 크기를 유지합니다. 앱 이름 Oni Exam과 예비색 배정은 이 구현의 제안이며 Figma 원본은 변경하지 않았습니다.

문제지 서체: 문제 본문 `신명 중명조` (장평 95%, 자간 -5%), 표·일러스트 `문체부 돋음체` (11.5pt, 장평 95%, 자간 -5%), 문항 번호·교시 제목 `한양견명조`, 5지선다형·단답형 번호 `신명 태고딕`, 수식·숫자 `HyhwpEQ`. 이 서체 파일들은 설치 패키지(`fonts/`)에 내장되어 앱 실행 및 변환 시 사용자 Windows 글꼴로 자동 설치됩니다.

## 배포 의존성

Tauri/React 및 Noto Sans KR 등 각 의존성의 라이선스를 유지해야 합니다. 특히 PyMuPDF/MuPDF는 AGPL 또는 상용 라이선스 선택을 제공하므로, 외부 배포 방식과 맞는 라이선스 구성을 확정해야 합니다. 참고: https://pymupdf.readthedocs.io/en/latest/about.html#license

앱 내 업데이트 기능(`check_update`, `install_update`)은 GitHub Releases API를 조회해 최신 설치 파일(`.exe`)을 내려받고 실행합니다. 코드 서명, 사용자 계정, 클라우드 동기화는 아직 구성하지 않았습니다.
