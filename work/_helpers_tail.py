# ---- 구역 설정 / 머리말·꼬리말
sec_pr = (
    '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" '
    'tabStopUnit="HWPUNIT" outlineShapeIDRef="1" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0">'
    '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0" />'
    '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0" />'
    '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" '
    'hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0" />'
    '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0" />'
    f'<hp:pagePr landscape="WIDELY" width="{u(842)}" height="{u(1191)}" gutterType="LEFT_ONLY">'
    f'<hp:margin header="0" footer="{u(args.footer)}" gutter="0" left="{u(87.8)}" right="{u(84.2)}" top="{u(107.8)}" bottom="{u(123.7)}" />'
    '</hp:pagePr>'
    '<hp:footNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0" />'
    '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000" />'
    '<hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850" /><hp:numbering type="CONTINUOUS" newNum="1" />'
    '<hp:placement place="EACH_COLUMN" beneathText="0" /></hp:footNotePr>'
    '<hp:endNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0" />'
    '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000" />'
    '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850" /><hp:numbering type="CONTINUOUS" newNum="1" />'
    '<hp:placement place="END_OF_DOCUMENT" beneathText="0" /></hp:endNotePr>'
    '<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417" /></hp:pageBorderFill>'
    '<hp:pageBorderFill type="EVEN" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417" /></hp:pageBorderFill>'
    '<hp:pageBorderFill type="ODD" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417" /></hp:pageBorderFill></hp:secPr>')

num_cp = char(F_SIN, 11.7, 100, 0)
ft_page_st = style('꼬리말 쪽번호', 'FooterPage', para('CENTER', line=16), num_cp)
ft_copy_st = style('꼬리말 저작권', 'FooterCopyright', para('LEFT', left=407.2, line=12, prev=3),
                   char(F_JUNG, 10, 90, 0, color='#0000FF'))
auto_page = ('<hp:run charPrIDRef="%d"><hp:ctrl><hp:autoNum num="1" numType="PAGE"><hp:autoNumFormat type="DIGIT" '
             'userChar="" prefixChar="" suffixChar="" supscript="0" /></hp:autoNum></hp:ctrl><hp:t> / 20</hp:t></hp:run>' % num_cp)
page_p = (f'<hp:p id="{nid()}" paraPrIDRef="{STYLES[ft_page_st][2]}" styleIDRef="{ft_page_st}" pageBreak="0" columnBreak="0" merged="0">{auto_page}</hp:p>')
page_box = tbl_host(table([[(page_p, None, 'CENTER')]], [50.5], [22], BF_BOX_THIN), ST_HOST_F)
footer_sub = (f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="TOP" linkListIDRef="0" '
              f'linkListNextIDRef="0" textWidth="{u(666.4)}" textHeight="{u(40)}" hasTextRef="0" hasNumRef="0">'
              + page_box + P('이 문제지에 관한 저작권은 한국교육과정평가원에 있습니다.', ft_copy_st)
              + '</hp:subList>')
footer_ctrl = f'<hp:ctrl><hp:footer id="{nid()}" applyPageType="BOTH">{footer_sub}</hp:footer></hp:ctrl>'
col1 = '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0" /></hp:ctrl>'
col2 = (f'<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="2" sameSz="1" sameGap="{u(28.2)}">'
        '<hp:colLine type="SOLID" width="0.4 mm" color="#000000" /></hp:colPr></hp:ctrl>')

