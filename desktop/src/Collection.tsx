import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { engine, chooseFolder } from './bridge';
type Row = {path:string; name:string; training:string; person:string; date:string; vendor:string; amount:string; text?:string; error:string};
export default function Collection() {
  const [kind,setKind]=useState('certificate');
  const [rows,setRows]=useState<Row[]>([]);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const fields = kind === 'certificate' ? ['training','person'] : ['date','vendor','amount'];
  const names:Record<string,string>={training:'연수명',person:'이수자 이름',date:'날짜',vendor:'사용처',amount:'금액'};
  async function read() {
    try {
      const paths=await open({multiple:true,filters:[{name:'PDF',extensions:['pdf']}]});
      if(!paths)return;
      setBusy(true);setMessage('파일을 읽고 있습니다. 첫 OCR 실행은 모델 다운로드가 필요합니다.');
      setRows(await engine<Row[]>({action:'collection_analyze',paths:typeof paths==='string'?[paths]:paths}));
      setMessage('인식 후보입니다. 원문을 확인하고 값을 수정한 뒤 저장하세요. 파일 하나에 여러 이수증이 있으면 먼저 분리해 주세요.');
    } catch(e){setMessage(String(e));}finally{setBusy(false);}
  }
  async function save(){
    try{
      const outputDir=await chooseFolder();if(!outputDir)return;
      setBusy(true);
      const results=await engine<{path:string;error:string}[]>({action:'collection_save',kind,rows,outputDir});
      setMessage(results.map(r=>r.error?`실패: ${r.path} — ${r.error}`:`저장: ${r.path}`).join('\n'));
    }catch(e){setMessage(String(e));}finally{setBusy(false);}
  }
  return <section className="panel" style={{padding:24}}>
    <h1>문서 취합</h1><p>이수증과 영수증을 읽고, 확인한 정보로 폴더와 파일명을 정리합니다. 원본은 보존됩니다.</p>
    <select disabled={busy} value={kind} onChange={e=>{setKind(e.target.value);setRows([]);}}><option value="certificate">이수증 취합</option><option value="receipt">영수증 취합</option></select>
    <button className="button" disabled={busy} onClick={()=>void read()}>PDF 여러 개 읽기</button>
    <p>{kind==='certificate'?'저장: 연수명 / 연수명(이름).pdf':'저장: YYYY-MM / 날짜_사용처_금액.pdf'}</p>
    {rows.map((row,i)=><div key={row.path} style={{borderTop:'1px solid #ddd',padding:16}}><strong>{row.name}</strong>{row.error&&<p role="alert">{row.error}</p>}
      <div style={{display:'flex',gap:12}}>{fields.map(key=><label key={key}>{names[key]}<input disabled={busy} value={String(row[key as keyof Row]||'')} onChange={e=>setRows(rows.map((r,n)=>n===i?{...r,[key]:e.target.value}:r))}/></label>)}</div>
      <details><summary>추출 원문 확인</summary><pre style={{whiteSpace:'pre-wrap'}}>{row.text}</pre></details>
      <button disabled={busy} onClick={()=>setRows(rows.filter((_,n)=>n!==i))}>제외</button></div>)}
    <button className="button primary" disabled={busy||!rows.length||rows.some(r=>r.error||fields.some(k=>!r[k as keyof Row]))} onClick={()=>void save()}>확인한 정보로 취합 저장</button>
    <p role="status" style={{whiteSpace:'pre-wrap'}}>{message}</p>
  </section>;
}
