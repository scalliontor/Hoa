#!/bin/sh
# Rebuilds the essay (one PDF): regenerate the tables from tools/model.py and the code, then compile.
# Usage: report/build.sh       (version, name and student id are read from report/author.tex)
set -e
cd "$(dirname "$0")/.."
python3 report/gen_tables.py
tectonic -X compile report/main.tex --outdir build/report --keep-logs
cp build/report/main.pdf build/report/tieuluan.pdf
field() { sed -n "s/.*\\\\newcommand{\\\\$1}{\\(.*\\)}.*/\\1/p" report/author.tex; }
VERSION=$(field essayVersion); ID=$(field studentId)
cp build/report/main.pdf "build/report/tieuluan_V${VERSION}_04_10_VUHUNGANH_$(echo "$ID" | tail -c 4).pdf"
echo "Overfull boxes: $(grep -c 'Overfull' build/report/main.log || true)"
grep -E "undefined (references|citations)|Reference .* undefined|Citation .* undefined" build/report/main.log | sort -u || true
python3 report/page_counts.py build/report/main.pdf 2>/dev/null || /usr/bin/python3 report/page_counts.py build/report/main.pdf
