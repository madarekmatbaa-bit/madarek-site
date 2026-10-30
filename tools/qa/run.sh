#!/usr/bin/env bash
# Site check before publishing (Ammar, 30 Oct: «اعمل مراجعة ماكنة … ما كل شوي بدي اكتشف مشكلة»).
#   python3 build.py && tools/qa/run.sh
# 1. every page at 360 px and 1280 px: sideways scrolling, script errors, broken first images, cut buttons
# 2. phone emulation (360/390/412) on the main page types: menu, search, languages, sideways swipe, scroll
# 3. header at 24 widths in ar/en/tr: nothing overlaps
# Needs node + playwright. Exit code 1 when anything is found.
set -u
cd "$(dirname "$0")/../.."
OUT=${QA_OUT:-/tmp/madarek-qa}; mkdir -p "$OUT"
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist >/dev/null 2>&1 & SRV=$!
trap 'kill $SRV' EXIT
sleep 1
(cd dist && find . -name index.html | sed 's|^\.||; s|index.html$||' | sort) > "$OUT/paths.txt"
fail=0
for w in 360 1280; do
  node tools/qa/qa_all.js http://127.0.0.1:8765 "$OUT/paths.txt" $w "$OUT/all_$w.json" | tee "$OUT/all_$w.log"
  grep -q "problems 0$" "$OUT/all_$w.log" || fail=1
done
node tools/qa/qa_mobile.js http://127.0.0.1:8765 tools/qa/phone_pages.json "$OUT/phone" | tee "$OUT/phone.log"
grep -q "issues 0$" "$OUT/phone.log" || fail=1
node tools/qa/hdrcheck.js http://127.0.0.1:8765 | tee "$OUT/header.log"
grep -q ":" <(grep -v "OK at all widths" "$OUT/header.log") && fail=1
echo "QA $([ $fail = 0 ] && echo passed || echo FOUND PROBLEMS) — details in $OUT"
exit $fail
