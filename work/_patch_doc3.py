import re
p = 'scripts/build_hwpx_doc3.py'
s = open(p, encoding='utf8').read()

def rep(a, b):
    global s
    assert a in s, a[:80]
    s = s.replace(a, b, 1)

rep("FONTS = ['HY신명조', 'HY견명조', 'HY중고딕', 'HY견고딕', 'Times New Roman']\nF_SIN, F_GYEON, F_JUNG, F_GYEONGO, F_TIMES = range(5)",
    "FONTS = ['HY신명조', 'HY견명조', 'HY중고딕', 'HY견고딕', 'Times New Roman', 'HY헤드라인M']\nF_SIN, F_GYEON, F_JUNG, F_GYEONGO, F_TIMES, F_HEAD = range(6)")
rep("4: 'FCAT_MYUNGJO'}", "4: 'FCAT_MYUNGJO', 5: 'FCAT_GOTHIC'}")
rep("FCLS = {'sin': F_SIN,", "FCLS = {'head': F_HEAD, 'sin': F_SIN,")
rep("def section_xml(sec_blocks, top_pt, start_page, header_pt, head_content, extra_ctrls):\n    out = []\n    if head_content:   # 1쪽: 머리 표가 든 문단 + 1단 정의 뒤 2단 전환\n        out.append(host_first(make_sec_pr(top_pt, start_page, header_pt), extra_ctrls, head_content))",
    "def section_xml(sec_blocks, top_pt, start_page, header_pt, head_content, extra_ctrls, head_extra=''):\n    out = []\n    if head_content:   # 1쪽: 머리 표가 든 문단 + 1단 정의 뒤 2단 전환\n        out.append(host_first(make_sec_pr(top_pt, start_page, header_pt), extra_ctrls, head_content) + head_extra)")

i = s.index("sec0 = section_xml(pages_first")
j = s.index("# ================================================================== 패키지")
mid_new = open('work/_mid_new.py', encoding='utf8').read()
pack = s[j:]
pack = pack.replace("if sec1: head = head.replace('secCnt=\"1\"', 'secCnt=\"2\"')", "head = head.replace('secCnt=\"1\"', f'secCnt=\"{len(secs)}\"')")
pack = pack.replace("if sec1: items = '<opf:item id=\"section1\" href=\"Contents/section1.xml\" media-type=\"application/xml\" />' + items",
                    "items = ''.join(f'<opf:item id=\"section{k}\" href=\"Contents/section{k}.xml\" media-type=\"application/xml\" />' for k in range(1, len(secs))) + items")
pack = pack.replace("if sec1: hpf = hpf.replace('<opf:itemref idref=\"section0\" linear=\"yes\" />', '<opf:itemref idref=\"section0\" linear=\"yes\" /><opf:itemref idref=\"section1\" linear=\"yes\" />')",
                    "hpf = hpf.replace('<opf:itemref idref=\"section0\" linear=\"yes\" />', '<opf:itemref idref=\"section0\" linear=\"yes\" />' + ''.join(f'<opf:itemref idref=\"section{k}\" linear=\"yes\" />' for k in range(1, len(secs))))")
pack = pack.replace("elif n == 'Contents/section0.xml': data = sec0.encode('utf-8')", "elif n == 'Contents/section0.xml': data = secs[0].encode('utf-8')")
pack = pack.replace("    if sec1: z.writestr('Contents/section1.xml', sec1.encode('utf-8'))", "    for k in range(1, len(secs)): z.writestr(f'Contents/section{k}.xml', secs[k].encode('utf-8'))")
s = s[:i] + mid_new + pack
open(p, 'w', encoding='utf8').write(s)
print('patched')
