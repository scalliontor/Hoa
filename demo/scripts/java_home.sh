#!/usr/bin/env bash
# Prints the bin folder of a JDK 17+ with jdk.httpserver: $JAVA_HOME, Homebrew openjdk@21, or any java on PATH.
for candidate in "${JAVA_HOME:-}/bin" /opt/homebrew/opt/openjdk@21/bin /usr/local/opt/openjdk@21/bin; do
  if [ -x "$candidate/javac" ]; then echo "$candidate"; exit 0; fi
done
if command -v javac >/dev/null 2>&1 && javac -version >/dev/null 2>&1; then dirname "$(command -v javac)"; exit 0; fi
echo "No JDK found. Install one with: brew install openjdk@21" >&2
exit 1
