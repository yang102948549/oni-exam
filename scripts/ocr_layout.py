"""Adapt kordoc OCR pixels to the existing top-left PDF-point line contract."""
import math
import unicodedata


def raw_from_ocr(page, width, height):
    scale = float(page['scale'])
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('OCR 좌표 배율이 올바르지 않습니다.')
    angle = math.radians(float(page.get('deskewAngle', 0)))
    cx, cy = (page['width'] - 1) / 2, (page['height'] - 1) / 2
    lines, rejected = [], 0
    for line in page['lines']:
        text = unicodedata.normalize('NFC', line.get('text', '')).strip()
        confidence = float(line.get('confidence', 0))
        if not text or line.get('dropped') or not math.isfinite(confidence) or confidence < 0.5:
            rejected += 1
            continue
        b = line['box']
        points = []
        for x, y in ((b['x'], b['y']), (b['x'] + b['w'], b['y']),
                     (b['x'], b['y'] + b['h']), (b['x'] + b['w'], b['y'] + b['h'])):
            points.append(((cx + (x-cx)*math.cos(angle) - (y-cy)*math.sin(angle))/scale,
                           (cy + (x-cx)*math.sin(angle) + (y-cy)*math.cos(angle))/scale))
        if not all(math.isfinite(v) for p in points for v in p):
            raise ValueError('OCR 줄 좌표가 올바르지 않습니다.')
        x0, y0 = max(0, min(p[0] for p in points)), max(0, min(p[1] for p in points))
        x1, y1 = min(width, max(p[0] for p in points)), min(height, max(p[1] for p in points))
        if x1 <= x0 or y1 <= y0:
            rejected += 1
            continue
        # OCR provides line boxes, not glyph metrics. Widths are estimates.
        weights = [1 if unicodedata.east_asian_width(c) in ('W', 'F') else 0.55 for c in text]
        unit = (x1-x0)/sum(weights)
        chars, x = [], x0
        for c, weight in zip(text, weights):
            right = x + weight*unit
            chars.append({'c': c, 'bbox': [x, y0, right, y1], 'origin': [x, y1]})
            x = right
        lines.append({'bbox': [x0, y0, x1, y1], 'spans': [
            {'font': 'OCR', 'size': min(18, max(6, (y1-y0)*0.85)), 'chars': chars}]})
    return {'blocks': [{'type': 0, 'lines': lines}]}, rejected


def structured_tables(blocks, number, height, top):
    """Only simple, single-column data grids fit the current HWPX grid contract.

    Merged/nested tables are left to the original layout extractor; never
    silently flatten their spans. kordoc boxes use bottom-left PDF points.
    """
    import pymupdf
    result = []
    for b in blocks:
        if b.get('type') != 'table' or b.get('pageNumber') != number or not b.get('bbox'):
            continue
        t, box = b['table'], b['bbox']
        rows, cols, cells = t['rows'], t['cols'], t['cells']
        if not (2 <= rows <= 50 and 2 <= cols <= 12) or len(cells) != rows:
            continue
        if any(len(row) != cols or any(c.get('colSpan', 1) != 1 or c.get('rowSpan', 1) != 1 or c.get('blocks') for c in row) for row in cells):
            continue
        x, y, w, h = box['x'], height-box['y']-box['height'], box['width'], box['height']
        if not (top < y < y+h < 1075 and w > 0 and h > 0) or x < 421 < x+w:
            continue
        runs = [[([{'t': c['text'], 'f': 'jung', 's': 11.5, 'ul': False, 'box': False, 'b': False, 'i': False}]
                  if c['text'] else []) for c in row] for row in cells]
        result.append({'rect': pymupdf.Rect(x, y, x+w, y+h),
                       'xs': [x+w*i/cols for i in range(cols+1)],
                       'ys': [y+h*i/rows for i in range(rows+1)], 'cells': runs})
    return result
