#!/usr/bin/env bash
# Build both versions of the paper from one source.
#   out/arxiv-src.tar.gz  — arXiv upload (named; source + generated numbers)
#   out/main-arxiv.pdf    — the same, compiled
#   out/main-anon.pdf     — double-anonymous journal submission (Financial Innovation)
set -euo pipefail
cd "$(dirname "$0")"
rm -rf out build && mkdir -p out build/arxiv build/anon
for v in arxiv anon; do
  cp main.tex build/$v/
  cp -r generated build/$v/
  [ "$v" = anon ] && touch build/$v/anon.flag
  (cd build/$v && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex >/dev/null)
  cp build/$v/main.pdf out/main-$v.pdf
done
# arXiv: sources only, no PDFs or aux files; arXiv compiles with pdflatex
(cd build/arxiv && tar czf ../../out/arxiv-src.tar.gz main.tex generated/*.tex)
# anonymity check: the anonymous PDF must not contain the author's identifiers
if pdftotext out/main-anon.pdf - | grep -E -i "akhtyamov|ravil|rav11l|0000-0002-0783|digital economy lab|yandex|zenodo|github" ; then
  echo "ANONYMITY CHECK FAILED" >&2; exit 1
fi
echo "built: $(ls out)"
