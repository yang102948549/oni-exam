import { invoke, isTauri } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

export const native = isTauri();
export async function engine<T>(request: Record<string, unknown>): Promise<T> {
  if (!native) throw new Error('파일 변환은 설치된 Oni Exam 앱에서 사용할 수 있습니다.');
  return invoke<T>('engine', { request });
}
export async function choosePdf() {
  if (!native) throw new Error('데스크탑 앱에서 PDF를 선택해 주세요. 현재 화면은 UI 미리보기입니다.');
  const file = await open({ multiple: false, title: '변환할 문제지 PDF 선택', filters: [{ name: 'PDF 문서', extensions: ['pdf'] }] });
  return typeof file === 'string' ? file : null;
}
export async function chooseFolder() {
  if (!native) throw new Error('저장 폴더는 데스크탑 앱에서 선택할 수 있습니다.');
  const folder = await open({ directory: true, multiple: false, title: '문제지를 저장할 폴더 선택' });
  return typeof folder === 'string' ? folder : null;
}
export const openLocal = (path: string) => invoke<void>('open_local', { path });
export const parentPath = (path: string) => path.slice(0, Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\')));
