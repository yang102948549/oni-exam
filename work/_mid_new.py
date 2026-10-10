def footer_ctrl_text(label):
    pp_ = (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[ft_page_st][2]}" styleIDRef="{ft_page_st}" pageBreak="0" columnBreak="0" merged="0">'
           f'{run(label, num_cp)}</hp:p>')
    bx = tbl_host(table([[(pp_, None, 'CENTER')]], [50.5], [22], BF_BOX_THIN), ST_HOST_F)
    sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
           f'textWidth="{u(666.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">' + bx + P(args.credit, ft_copy_st) + '</hp:subList>')
    return f'<hp:ctrl><hp:footer id="{nid()}" applyPageType="BOTH">{sub}</hp:footer></hp:ctrl>'

def cell_par(runs, align, line=36):
    pp = para(align, line=line)
    st = style('머리 셀', 'HeaderCell', pp, runs[0][1])
    return (f'<hp:p id="{nid()}" paraPrIDRef="{pp}" styleIDRef="{st}" pageBreak="0" columnBreak="0" merged="0">'
            + ''.join(run(t, c) for t, c in runs) + '</hp:p>')

def header_custom(left, right, la, ra):
    tb = table([[(cell_par(left, la), None, 'CENTER'), (blank, None, 'CENTER'), (cell_par(right, ra), None, 'CENTER')]],
               [250, 170.4, 250], [37], BF_NONE)
    sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
           f'textWidth="{u(670.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">' + tbl_host(tb, ST_HOST) + '</hp:subList>')
    return f'<hp:ctrl><hp:header id="{nid()}" applyPageType="BOTH">{sub}</hp:header></hp:ctrl>'

def soc_head():
    big = char(F_GYEON, 31.3, 100, 0); ttl = char(F_GYEONGO, 37.9, 100, 0); sm = char(F_HEAD, 20, 100, 0)
    r1 = [(blank, None, 'CENTER'), (hd_title, None, 'CENTER'), (cell_par([('1', big)], 'RIGHT'), None, 'CENTER')]
    area = cell_par([('사회탐구 영역', ttl), ('(' + args.sub + ')', sm)], 'CENTER', 46)
    r2 = [(hd_period, None, 'CENTER'), (area, None, 'CENTER'), (blank, None, 'CENTER')]
    top = table([r1, r2], [96, 480, 90.4], [39, 62], BF_NONE)
    lab = char(F_JUNG, 15.2, 100, 0)
    def c(t=''): return cell_par([(t, lab)], 'CENTER', 20)
    cells = ([('성명', 39, 3), ('', 148, 3), ('', 16, 1), ('수험 번호', 71, 3)] + [('', 22, 3)] * 4 + [('-', 18, 3)]
             + [('', 20, 3)] * 4 + [('', 16, 1), ('제(    )선택', 88, 3)])
    gt = table([[(c(t), bf_, 'CENTER') for t, w, bf_ in cells]], [w for t, w, bf_ in cells], [24], BF_NONE)
    outer_pp = para('LEFT', left=47, pct=True)
    st_o = style('성명 칸 문단', 'NameFieldHost', outer_pp, char())
    grid_host = (f'<hp:p id="{nid()}" paraPrIDRef="{outer_pp}" styleIDRef="{st_o}" pageBreak="0" columnBreak="0" merged="0">'
                 f'<hp:run charPrIDRef="{STYLES[st_o][3]}">{gt}</hp:run></hp:p>')
    rule = table([[(grid_host, BF_RULE, 'CENTER')]], [666.4], [38], BF_NONE)
    return top, tbl_host(rule, ST_HOST)

SOC = args.preset == 'soc'
secs = []
if SOC:
    fn = [x for x in args.footer_nums.split(',') if x]
    pgs = sorted({b['page'] for b in blocks})
    for idx, pg in enumerate(pgs):
        bl = [b for b in blocks if b['page'] == pg]
        flabel = f"{fn[idx] if idx < len(fn) else pg} / {args.total}"
        fctrl = footer_ctrl_text(flabel)
        if idx == 0:
            top_tbl, rule_para = soc_head()
            secs.append(section_xml(bl, 107.8, 1, 0, top_tbl, fctrl, head_extra=rule_para))
        else:
            big = char(F_GYEON, 31.3, 100, 0); sm = char(F_HEAD, 20, 100, 0); ttl = char(F_GYEONGO, 28, 100, 0)
            sub_ = '(' + args.sub + ')'
            if pg % 2 == 0:
                hdr = header_custom([(str(pg), big), (' ' + sub_, sm)], [('사회탐구 영역', ttl)], 'LEFT', 'RIGHT')
            else:
                hdr = header_custom([('사회탐구 영역', ttl)], [(args.sub, char(F_HEAD, 20, 100, 0, box=True)), (' ' + str(pg), big)], 'LEFT', 'RIGHT')
            secs.append(section_xml(bl, args.top2, pg, args.hdr2, '', fctrl + hdr))
else:
    secs.append(section_xml(pages_first, 107.8, 1, 0, head_tbl, footer_ctrl))
    if rest:
        secs.append(section_xml(rest, args.top2, 2, args.hdr2, '',
                    footer_ctrl.replace(footer_ctrl.split('"')[1], str(nid()), 1) + header_xml('EVEN') + header_xml('ODD')))

