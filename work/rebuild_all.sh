set -e
cd "C:/Users/yang4/OneDrive/claude/PDF파싱"
python -X utf8 scripts/extract_items4.py 국어.pdf 1 3 work/items_ko4.json --lang ko --figdir work/figs_ko > /dev/null
python -X utf8 scripts/fit_pages.py work/items_ko4.json output/native_p3/ko.hwpx -- --subject 국어 --period "제1 교시" --total 20 --lang ko --top2 108 --hdr2 51 --ratio 100 --spacing 0 --pratio 100 --pspacing 0 | tail -2
python -X utf8 scripts/fit_pages.py work/items_en_1_3.json output/native_en3/en.hwpx -- --subject 영어 --period "제 3교시" --total 8 --lang en --top2 108 --hdr2 51 | tail -2
python -X utf8 scripts/extract_items4.py test_inputs/2026학년도_수능/사회탐구/2026학년도_수능_사회탐구_생활과윤리_문제.pdf 1 3 work/items_soc4.json --lang soc --math --figdir work/figs_soc4 > /dev/null
python -X utf8 scripts/fit_pages.py work/items_soc4.json output/native_soc3/soc.hwpx -- --preset soc --area 사회탐구 --sub "생활과 윤리" --period "제4 교시" --total 36 --footer-nums 1,2,35 --lang ko --top2 108 --hdr2 51 | tail -2
python -X utf8 scripts/fit_pages.py work/items_math_1_3.json output/native_math3/math.hwpx -- --subject 수학 --period "제 2교시" --total 20 --lang ko --top2 108 --hdr2 51 | tail -2
echo ALLDONE
