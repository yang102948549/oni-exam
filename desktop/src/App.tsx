import { useCallback, useEffect, useRef, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { getCurrentWebview } from '@tauri-apps/api/webview';
import { ArrowDownToLine, ArrowRight, BookOpen, Check, CheckCircle2, ChevronLeft, ChevronRight, CircleHelp, Clock3, FileCheck2, FilePlus2, FileText, FolderOpen, History, Info, Loader2, LockKeyhole, Monitor, Plus, Search, Settings2, ShieldCheck, SlidersHorizontal, Type, Upload, X } from 'lucide-react';
import { chooseFolder, choosePdf, engine, native, openLocal, parentPath } from './bridge';
import type { Environment, Job, PdfInfo, Progress, Settings } from './types';

type View = 'convert' | 'history' | 'settings' | 'help';
const labels: Record<View, string> = { convert: '새 문제지', history: '작업 기록', settings: '환경 설정', help: '사용 안내' };
const subjects = ['국어', '영어', '수학', '한국사', '사회탐구', '과학탐구'];
const fontRoles = ['본문 · serif', '제목 · sans', '숫자 · 기호', '수식'];
const fontNames = ['KoPub World 바탕체', 'KoPub World 돋움체', 'KoPub World 돋움체', 'HyhwpEQ'];
const dateText = (s: string) => new Intl.DateTimeFormat('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(s));
const sizeText = (n: number) => n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`;

function JobRows({ jobs, onOpen }: { jobs: Job[]; onOpen: (p: string) => void }) {
  return <div className="job-list">{jobs.map(job => <div className="job-row" key={job.id}>
    <div className="file-icon small"><FileText size={18}/></div>
    <div className="job-name"><strong title={job.name}>{job.name}</strong><span>{job.subject} · {job.first_page}–{job.last_page}쪽 <span className="dot-divider">·</span> {dateText(job.created_at)}</span>{job.status === 'failed' && <span className="error-text">{job.message}</span>}</div>
    <span className={`badge ${job.status === 'done' ? 'success' : job.status === 'failed' ? 'danger' : 'neutral'}`}>{job.status === 'done' ? <><Check size={12}/>완료</> : job.status === 'failed' ? '실패' : '미완료'}</span>
    <button className="icon-button" aria-label={`${job.name} 저장 폴더 열기`} onClick={() => onOpen(parentPath(job.output))}><FolderOpen size={17}/></button>
    <button className="button small-button" disabled={job.status !== 'done'} onClick={() => onOpen(job.output)}>열기<ArrowRight size={14}/></button>
  </div>)}</div>;
}

export default function App() {
  const [view, setView] = useState<View>('convert');
  const [pdf, setPdf] = useState<PdfInfo | null>(null);
  const [subject, setSubject] = useState('국어');
  const [title, setTitle] = useState('수능형 연습 문제지');
  const [subtitle, setSubtitle] = useState('');
  const [first, setFirst] = useState(1);
  const [last, setLast] = useState(1);
  const [math, setMath] = useState(false);
  const [outputDir, setOutputDir] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [env, setEnv] = useState<Environment | null>(null);
  const [loading, setLoading] = useState(false);
  const [converting, setConverting] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [result, setResult] = useState<Job | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [previewPage, setPreviewPage] = useState(1);
  const [preview, setPreview] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [search, setSearch] = useState('');
  const busyRef = useRef(false);
  const previewId = useRef(0);
  const pending = loading || converting;
  const fail = useCallback((e: unknown) => setError(String(e instanceof Error ? e.message : e)), []);
  const refreshHistory = useCallback(() => engine<Job[]>({ action: 'history' }).then(setJobs).catch(fail), [fail]);

  useEffect(() => {
    if (!native) return;
    void refreshHistory();
    void engine<Settings>({ action: 'settings' }).then(s => setOutputDir(s.outputDir)).catch(fail);
    void engine<Environment>({ action: 'environment' }).then(setEnv).catch(fail);
    const stops = [listen<Progress>('engine-progress', e => setProgress(e.payload)), listen<string>('close-blocked', e => setNotice(e.payload))];
    return () => { stops.forEach(p => { void p.then(stop => stop()); }); };
  }, [fail, refreshHistory]);
  useEffect(() => { if (!notice) return; const t = setTimeout(() => setNotice(''), 6000); return () => clearTimeout(t); }, [notice]);

  const loadPdf = useCallback(async (path: string) => {
    if (busyRef.current) return;
    busyRef.current = true; setLoading(true); setError(''); setResult(null); setProgress(null); setView('convert');
    previewId.current++;
    try {
      const info = await engine<PdfInfo>({ action: 'inspect', path });
      setPdf(info); setSubject(info.subject); setMath(['수학', '과학탐구'].includes(info.subject)); setFirst(1); setLast(info.pages); setSubtitle('');
      setPreviewPage(1); setPreview(info.thumbnail); setPreviewLoading(false);
      setOutputDir(prev => prev || parentPath(info.path));
    } catch (e) { fail(e); }
    finally { busyRef.current = false; setLoading(false); setDragging(false); }
  }, [fail]);
  const pickFile = useCallback(async () => { if (busyRef.current) return; try { const p = await choosePdf(); if (p) await loadPdf(p); } catch (e) { fail(e); } }, [loadPdf, fail]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'o') { e.preventDefault(); void pickFile(); } };
    window.addEventListener('keydown', handler);
    const stop = native ? getCurrentWebview().onDragDropEvent(e => {
      if (busyRef.current) return;
      setDragging(e.payload.type === 'over' || e.payload.type === 'enter');
      if (e.payload.type === 'drop' && e.payload.paths.length) void loadPdf(e.payload.paths[0]);
    }) : null;
    return () => { window.removeEventListener('keydown', handler); if (stop) void stop.then(f => f()); };
  }, [loadPdf, pickFile]);

  async function folder() {
    try { const p = await chooseFolder(); if (p) { setOutputDir(p); await engine({ action: 'save_settings', value: { outputDir: p } }); } } catch (e) { fail(e); }
  }
  async function turnPage(page: number) {
    if (!pdf || page < 1 || page > pdf.pages) return;
    const id = ++previewId.current;
    setPreviewLoading(true); setPreviewPage(page);
    try { const r = await engine<{ thumbnail: string }>({ action: 'preview', path: pdf.path, page }); if (id === previewId.current) setPreview(r.thumbnail); }
    catch (e) { if (id === previewId.current) fail(e); }
    finally { if (id === previewId.current) setPreviewLoading(false); }
  }
  const rangeValid = !!pdf && Number.isInteger(first) && Number.isInteger(last) && first >= 1 && last >= first && last <= pdf.pages;
  async function convert() {
    if (!pdf || !rangeValid || !outputDir || busyRef.current) return;
    busyRef.current = true; setConverting(true); setError(''); setResult(null); setProgress({ stage: 'prepare', percent: 5, message: '문제지 변환을 준비하고 있어요.' });
    try {
      const done = await engine<Job>({ action: 'convert', path: pdf.path, first, last, subject, title, subtitle, math, outputDir });
      setResult(done);
    } catch (e) { fail(e); setProgress(null); }
    finally { busyRef.current = false; setConverting(false); void refreshHistory(); }
  }
  function reset() { if (pending) return; previewId.current++; setPdf(null); setPreview(''); setResult(null); setProgress(null); setError(''); }
  const open = (path: string) => { void openLocal(path).catch(fail); };
  const filtered = jobs.filter(j => `${j.name} ${j.subject}`.toLowerCase().includes(search.toLowerCase()));

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><img src="/brand/oni-exam.svg" alt=""/><span>Oni <b>Exam</b></span><span className="brand-caption">BETA</span></div>
      <div className="workspace-label">문제지 작업실</div>
      <nav aria-label="주 메뉴">
        <button className={`nav-item ${view === 'convert' ? 'active' : ''}`} onClick={() => setView('convert')}><FilePlus2 size={18}/>새 문제지<span className="nav-plus"><Plus size={14}/></span></button>
        <button className={`nav-item ${view === 'history' ? 'active' : ''}`} onClick={() => { setView('history'); if (native) void refreshHistory(); }}><History size={18}/>작업 기록{jobs.length > 0 && <span className="nav-count">{jobs.length}</span>}</button>
      </nav>
      <div className="sidebar-bottom">
        <div className="local-note"><ShieldCheck size={17}/><div><strong>내 PC에서 안전하게</strong><p>파일은 서버에 업로드되지 않아요.</p></div></div>
        <button className={`nav-item ${view === 'settings' ? 'active' : ''}`} onClick={() => setView('settings')}><Settings2 size={18}/>환경 설정</button>
        <button className={`nav-item ${view === 'help' ? 'active' : ''}`} onClick={() => setView('help')}><CircleHelp size={18}/>사용 안내</button>
        <div className="sidebar-footer"><span>Oni School</span><span>v0.1.0</span></div>
      </div>
    </aside>
    <div className="app-body">
      <header className="topbar"><div><span className="muted">작업실</span><ChevronRight size={13}/><span>{labels[view]}</span></div><span className="local-status"><i/>{native ? '로컬 작업 공간' : '화면 미리보기'}</span></header>
      <main>
        {error && <div className="alert error" role="alert"><Info size={17}/><span>{error}</span><button aria-label="오류 메시지 닫기" onClick={() => setError('')}><X size={16}/></button></div>}
        {notice && <div className="toast" role="status"><Info size={16}/>{notice}</div>}
        {view === 'convert' && <>
          <div className="page-heading"><div><div className="eyebrow"><span/> PDF TO HWPX</div><h1>수업 준비에, 한결 여유를.</h1><p>PDF 문제지를 편집 가능한 한글 문서로 바꿔보세요.</p></div><span className="heading-tag"><LockKeyhole size={14}/>오프라인 변환</span></div>
          <div className="workflow"><span className="current"><b>1</b>파일 선택</span><div/><span className={pdf ? 'current' : ''}><b>2</b>변환 설정</span><div/><span className={result ? 'current' : ''}><b>3</b>문제지 완성</span></div>
          <div className="workspace-grid">
            <div className="editor-column">
              <section className="panel source-panel"><div className="panel-heading"><h2><FileText size={17}/>원본 문제지</h2><span className="caption">PDF</span></div>
                {!pdf ? <button className={`dropzone ${dragging ? 'dragging' : ''}`} onClick={() => void pickFile()} disabled={pending}>
                  <span className="upload-emblem">{loading ? <Loader2 size={26} className="spin"/> : <Upload size={26}/>}</span><strong>{loading ? '파일을 살펴보고 있어요' : '문제지 PDF를 여기에 놓아주세요'}</strong><span>또는 클릭해서 내 PC의 파일 선택</span><span className="drop-hint">수능형 2단 문제지 · PDF 최대 300MB <kbd>Ctrl O</kbd></span>
                </button> : <div className="selected-file"><div className="file-icon"><FileText size={24}/></div><div><strong title={pdf.name}>{pdf.name}</strong><span>{pdf.pages}페이지 <span className="dot-divider">·</span> {sizeText(pdf.size)}</span></div><button className="icon-button" aria-label="선택한 PDF 제거" disabled={pending} onClick={reset}><X size={17}/></button></div>}
                {pdf?.warnings.map(w => <div className="inline-warning" key={w}><Info size={15}/><span>{w}</span></div>)}
              </section>
              <section className="panel settings-panel"><div className="panel-heading"><h2><SlidersHorizontal size={17}/>변환 설정</h2><span className="caption">기본 양식</span></div>
                <label className="field title-field">문제지 제목<input value={title} maxLength={60} disabled={pending} onChange={e => setTitle(e.target.value)} placeholder="문제지 제목을 입력하세요"/></label>
                <div className="form-grid"><label className="field">과목<select aria-label="과목" value={subject} disabled={pending} onChange={e => { setSubject(e.target.value); setMath(['수학', '과학탐구'].includes(e.target.value)); }}>{subjects.map(s => <option key={s}>{s}</option>)}</select></label><div className="field">변환할 페이지<div className="range"><input aria-label="시작 페이지" type="number" min={1} max={pdf?.pages || 1} value={first} disabled={!pdf || pending} onChange={e => setFirst(Number(e.target.value))}/><span>–</span><input aria-label="끝 페이지" type="number" min={first} max={pdf?.pages || 1} value={last} disabled={!pdf || pending} onChange={e => setLast(Number(e.target.value))}/><span className="unit">쪽</span></div></div></div>
                {['사회탐구', '과학탐구'].includes(subject) && <label className="field subtitle-field">세부 과목<input value={subtitle} maxLength={60} placeholder="예: 사회·문화, 물리학Ⅰ" disabled={pending} onChange={e => setSubtitle(e.target.value)}/></label>}
                {pdf && !rangeValid && <p className="error-text">1~{pdf.pages}쪽 안에서 시작·끝 페이지를 지정해 주세요.</p>}
                <label className="check-row"><input type="checkbox" checked={math} disabled={pending} onChange={e => setMath(e.target.checked)}/><span>수식 및 도형 분석<span className="caption">수학·과학 문제지에 권장</span></span><span className="badge neutral">실험 기능</span></label>
                <div className="font-summary"><Type size={16}/><div><strong>Oni 기본 글꼴</strong><span>KoPub World 바탕체 · 돋움체 · HyhwpEQ</span></div><button className="text-button" onClick={() => setView('settings')}>확인<ChevronRight size={13}/></button></div>
                <div className="field output-field">저장 위치<div className="folder-field"><FolderOpen size={16}/><span title={outputDir}>{outputDir || '원본 파일을 선택하면 같은 폴더에 저장해요'}</span><button onClick={() => void folder()} disabled={pending}>변경</button></div></div>
                <button className="button primary convert-button" onClick={() => void convert()} disabled={pending || !pdf || !pdf.hasText || !pdf.compatible || !rangeValid || !outputDir}>{converting ? <Loader2 size={17} className="spin"/> : <ArrowDownToLine size={17}/>} {converting ? '문제지 만드는 중' : '한글 문제지 만들기'}{!converting && <ArrowRight size={17}/>}</button>
                <p className="save-note">HWPX로 저장 · 원본 PDF는 그대로 보관됩니다.</p>
              </section>
            </div>
            <section className="panel preview-panel"><div className="panel-heading"><h2><BookOpen size={17}/>원본 미리보기</h2><span className="badge neutral">PDF</span></div><div className={`preview-stage ${pdf ? 'has-pdf' : ''}`}>
              {preview ? <><img src={preview} alt={`원본 PDF ${previewPage}쪽`} className={previewLoading ? 'faded' : ''}/>{previewLoading && <Loader2 className="preview-spinner spin" size={24}/>}</> : <div className="preview-empty"><div className="paper-stack"><div className="paper-back"/><div className="paper-front"><span className="paper-title"/><div className="paper-rule"/><div className="paper-columns">{[0,1].map(n => <div key={n}>{Array.from({ length: 9 }, (_, i) => <i key={i} />)}</div>)}</div><div className="paper-number"/></div><span className="preview-badge"><FileText size={19}/></span></div><strong>문제지가 놓일 자리예요</strong><p>PDF를 선택하면<br/>페이지별로 미리 볼 수 있어요.</p></div>}
            </div><div className="preview-footer"><span>{pdf ? `${pdf.pages}페이지 문서` : '파일을 먼저 선택해 주세요'}</span><div><button className="icon-button" aria-label="이전 페이지" disabled={!pdf || previewPage <= 1 || previewLoading} onClick={() => void turnPage(previewPage - 1)}><ChevronLeft size={16}/></button><span>{pdf ? previewPage : '–'} <span className="muted">/ {pdf ? pdf.pages : '–'}</span></span><button className="icon-button" aria-label="다음 페이지" disabled={!pdf || previewPage >= pdf.pages || previewLoading} onClick={() => void turnPage(previewPage + 1)}><ChevronRight size={16}/></button></div></div></section>
          </div>
          {progress && <section className={`panel progress-panel ${result ? 'finished' : ''}`} aria-live="polite"><div className="progress-heading">{result ? <CheckCircle2 size={21}/> : <Loader2 className="spin" size={21}/>}<div><strong>{progress.message}</strong><p>{result ? '한글에서 문서를 열어 줄바꿈과 수식 배치를 확인해 주세요.' : '파일의 양에 따라 시간이 걸릴 수 있어요. 잠시만 기다려 주세요.'}</p></div>{result ? <button className="button primary" onClick={() => open(result.output)}>한글에서 열기<ArrowRight size={15}/></button> : <span>{progress.percent}%</span>}</div><progress value={progress.percent} max={100}/>{result && <div className="result-path"><span title={result.output}>{result.output}</span><button className="text-button" onClick={() => open(parentPath(result.output))}>저장 폴더 열기<FolderOpen size={14}/></button></div>}</section>}
          <section className="recent"><div className="section-heading"><h2>최근 작업</h2><button className="text-button" onClick={() => setView('history')}>전체 보기<ChevronRight size={14}/></button></div>{jobs.length ? <JobRows jobs={jobs.slice(0,3)} onOpen={open}/> : <div className="history-empty"><Clock3 size={18}/><span>완성한 문제지는 여기에 차곡차곡 모여요.</span></div>}</section>
        </>}
        {view === 'history' && <><div className="page-heading"><div><div className="eyebrow">YOUR WORKSPACE</div><h1>작업 기록</h1><p>이 PC에서 만든 문제지를 다시 열어보세요.</p></div><button className="button primary" onClick={() => setView('convert')}><Plus size={16}/>새 문제지</button></div><div className="history-toolbar"><span>전체 <strong>{jobs.length}</strong>개</span><label className="search"><Search size={16}/><input aria-label="작업 검색" placeholder="파일명 또는 과목 검색" value={search} onChange={e => setSearch(e.target.value)}/></label></div><section className="panel">{filtered.length ? <JobRows jobs={filtered} onOpen={open}/> : <div className="large-empty"><History size={32}/><h2>{search ? '검색 결과가 없어요' : '아직 작업 기록이 없어요'}</h2><p>{search ? '다른 파일명이나 과목으로 검색해 보세요.' : '첫 문제지를 만들면 이곳에서 다시 찾을 수 있어요.'}</p>{!search && <button className="button" onClick={() => setView('convert')}>문제지 만들러 가기<ArrowRight size={15}/></button>}</div>}</section></>}
        {view === 'settings' && <><div className="page-heading"><div><div className="eyebrow">PREFERENCES</div><h1>편안한 작업을 위한 설정</h1><p>저장 위치와 문서에 사용할 글꼴을 확인하세요.</p></div></div><section className="panel preferences"><div className="panel-heading"><h2><FolderOpen size={18}/>기본 저장 위치</h2></div><div className="preference-content"><p>새로운 문제지를 저장할 폴더입니다. 선택하면 자동으로 저장돼요.</p><div className="folder-field"><FolderOpen size={16}/><span title={outputDir}>{outputDir || '원본 PDF와 같은 폴더'}</span><button disabled={pending} onClick={() => void folder()}>폴더 선택</button></div></div></section><section className="panel preferences"><div className="panel-heading"><h2><Type size={18}/>문제지 글꼴</h2><span className="caption">지정된 기본 서체</span></div><div className="font-list">{fontNames.map((f, i) => <div className="font-row" key={fontRoles[i]}><span>{fontRoles[i]}</span><strong>{f}</strong><span className={`badge ${env?.fonts[i].installed ? 'success' : 'neutral'}`}>{env ? env.fonts[i].installed ? <><Check size={12}/>설치됨</> : '설치 확인 필요' : '앱에서 확인'}</span></div>)}</div><p className="preference-note"><Info size={15}/>글꼴이 없으면 한글에서 다른 글꼴로 표시될 수 있어요. 글꼴 파일은 앱에 포함되지 않습니다.</p></section><section className="panel preferences"><div className="panel-heading"><h2><Monitor size={18}/>실행 환경</h2><button className="text-button" onClick={() => { void engine<Environment>({ action: 'environment' }).then(setEnv).catch(fail); }}>다시 확인</button></div><div className="font-list"><div className="font-row"><span>한글 프로그램</span><strong>{env ? env.hancom ? '한글 설치 확인됨' : '한글 설치 확인 필요' : '데스크탑 앱에서 확인'}</strong></div><div className="font-row"><span>저장 방식</span><strong>로컬 파일 · SQLite 작업 기록</strong><LockKeyhole size={15}/></div></div><p className="preference-note">HWPX 생성은 한글 없이 가능합니다. 문서 편집과 최종 배치 확인에는 한글이 필요합니다.</p></section></>}
        {view === 'help' && <><div className="page-heading"><div><div className="eyebrow">GETTING STARTED</div><h1>첫 문제지를 만들어볼까요?</h1><p>원본을 고르고, 필요한 범위를 정하면 준비가 끝나요.</p></div></div><section className="panel help-panel">{[{ icon: Upload, title: '수능형 PDF를 선택하세요', text: '텍스트를 선택할 수 있는 842 × 1191pt 크기의 2단 문제지를 지원합니다. 스캔본이나 다른 판형은 현재 지원하지 않습니다.' },{ icon: SlidersHorizontal, title: '과목과 페이지를 지정하세요', text: '필요한 페이지만 골라 변환할 수 있어요. 수학·과학은 수식 및 도형 분석을 켜주세요. 수식 인식은 실험 기능으로 결과 검토가 필요합니다.' },{ icon: FileCheck2, title: '한글에서 마무리하세요', text: '생성된 HWPX에는 편집 가능한 문단과 수식이 들어갑니다. 원본 미리보기와 비교하며 누락, 줄바꿈, 도형과 수식 배치를 확인하세요. 원본과 완전히 같은 조판은 보장하지 않습니다.' }].map((x,i) => <div className="help-step" key={x.title}><span className="help-step-icon"><x.icon size={23}/></span><div><span className="caption">STEP 0{i+1}</span><h2>{x.title}</h2><p>{x.text}</p></div></div>)}</section><div className="help-bottom"><ShieldCheck size={20}/><p>원본과 변환 파일은 내 PC에 보관됩니다.<br/>로그인이나 인터넷 연결 없이 작업할 수 있어요.</p></div></>}
        <footer className="page-footer"><span>수업과 기록을 더 편안하게.</span><span>Oni School</span></footer>
      </main>
    </div>
  </div>;
}
