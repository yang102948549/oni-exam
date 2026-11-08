// Local file bridge; stdout is reserved for machine-readable results.
import { parse, markdownToHwpx, blocksToMarkdown } from 'kordoc';
import { readFile, writeFile } from 'node:fs/promises';

const request = JSON.parse(await readFile(process.argv[2], 'utf8'));
try {
const result = await parse(request.path, {
  pages: request.pages,
  ocr: request.force ? 'force' : request.readOnly || request.general && request.ocr !== 'off' ? true : false,
  ocrLines: request.force || request.general ? 'all' : false,
  ocrRec: 'printed',
  ocrDetLongSide: 1920,
  images: Boolean(request.general),
  imagePlacement: 'flow',
  dropBlankImages: true,
  formulaOcr: false,
});
if (request.general && result.success) {
  const warnings = result.warnings ?? [];
  const needs = (result.pageQuality ?? []).filter(p => p.needsOcr);
  if ((request.ocr === 'off' && needs.length) || warnings.some(w => /OCR_FAILED|OCR_UNAVAILABLE/.test(JSON.stringify(w)))) {
    throw new Error('OCR이 필요한 페이지를 읽지 못했습니다. OCR 설정과 모델 다운로드를 확인해 주세요.');
  }
  if (!result.markdown?.trim()) throw new Error('추출할 문서 내용이 없습니다.');
  const generatedWarnings = [];
  // A full-sheet scan is a background. Keeping it in the document would
  // duplicate the recognized body. Keep smaller illustrations untouched.
  const fullOcrPages = new Map((result.ocrLines ?? [])
    .filter(p => !p.regionsOnly && p.lines.some(l => !l.dropped && l.text?.trim()))
    .map(p => [p.pageNumber, p]));
  const filtered = result.blocks.filter(b => {
    const p = fullOcrPages.get(b.pageNumber);
    return !(b.type === 'image' && p && b.bbox &&
      b.bbox.width * b.bbox.height >= 0.85 * p.width * p.height / (p.scale * p.scale));
  });
  if (filtered.length !== result.blocks.length) {
    result.blocks = filtered;
    result.markdown = blocksToMarkdown(filtered);
    generatedWarnings.push('OCR 본문과 중복되는 전체 페이지 배경 이미지를 제외했습니다. 스캔 속 그림은 원본과 확인해 주세요.');
  }
  const bytes = await markdownToHwpx(result.markdown, {
    images: Object.fromEntries((result.images ?? []).map(img => [img.filename, img.data])),
    inlineMath: Boolean(request.math), warnings: generatedWarnings,
  });
  await writeFile(request.hwpx, Buffer.from(bytes));
  result.generatedWarnings = generatedWarnings;
  // Binary image data is already embedded in HWPX; do not duplicate it in JSON.
  delete result.images;
  for (const block of result.blocks ?? []) delete block.imageData;
}
await writeFile(request.output, JSON.stringify(result));
if (!result.success) process.exitCode = 2;
} catch (error) {
  await writeFile(request.output, JSON.stringify({success: false, error: String(error.message ?? error)}));
  process.exitCode = 2;
}
