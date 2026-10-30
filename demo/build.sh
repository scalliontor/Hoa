#!/usr/bin/env bash
# Compiles the Họa. demo into build/classes (no build tool: javac and the jars in lib/).
set -euo pipefail
cd "$(dirname "$0")"
JAVA_BIN="$(scripts/java_home.sh)"
rm -rf build/classes && mkdir -p build/classes
"$JAVA_BIN/javac" --release 17 -encoding UTF-8 -Xlint:unchecked -cp "lib/*" -d build/classes \
  $(find src/main/java -name "*.java")
echo "Compiled $(find src/main/java -name '*.java' | wc -l | tr -d ' ') Java files into build/classes"
