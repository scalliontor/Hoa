#!/bin/sh
# Rebuilds the Vietnamese presentation guide: numbers and slide titles are read from the project first
# (guide/gen_facts.py), then guide/main.tex is compiled with tectonic. Output: guide/guide_thuyet_trinh_Hoa.pdf
set -e
cd "$(dirname "$0")/.."
slides/.venv/bin/python guide/gen_facts.py
tectonic -X compile guide/main.tex --outdir build/guide --keep-logs
cp build/guide/main.pdf guide/guide_thuyet_trinh_Hoa.pdf
echo "Overfull boxes: $(grep -c 'Overfull' build/guide/main.log || true)"
grep -E "Missing character|undefined (references|control)|Undefined control|Reference .* undefined|LaTeX Error" build/guide/main.log | sort -u | head -20 || true
echo "Wrote guide/guide_thuyet_trinh_Hoa.pdf"
