#!/usr/bin/env bash
# Compiles and runs the tests (tests/java, no framework), then checks the code against tools/model.py.
# Both reports are written to ../build/test_results.txt for Chapter 5.
set -uo pipefail
cd "$(dirname "$0")"
JAVA_BIN="$(scripts/java_home.sh)"
REPORT=../build/test_results.txt
mkdir -p ../build build
rm -rf build/test-classes && mkdir -p build/test-classes
"$JAVA_BIN/javac" --release 17 -encoding UTF-8 -cp "lib/*" -d build/test-classes \
  $(find src/main/java tests/java -name "*.java") || exit 1
{
  echo "Họa. demo — test run $(date '+%Y-%m-%d %H:%M')"
  "$JAVA_BIN/java" -Dfile.encoding=UTF-8 -Djava.awt.headless=true -cp "build/test-classes:lib/*" com.ptit.ecom.test.TestRunner
  tests=$?
  echo
  echo "== Code versus model (tools/check_code_model.py)"
  python3 ../tools/check_code_model.py
  model=$?
  exit $(( tests || model ))
} 2>&1 | tee "$REPORT"
status=${PIPESTATUS[0]}
echo "Report: build/test_results.txt"
exit "$status"
