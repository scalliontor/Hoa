#!/usr/bin/env bash
# Starts the self-hosted Whisper voice server (voice-server/run_voice.sh) and the Họa. web shop.
# Usage: ./run.sh [config file]   (default config/app.properties -> http://127.0.0.1:8686)
set -euo pipefail
cd "$(dirname "$0")"
JAVA_BIN="$(scripts/java_home.sh)"
mkdir -p data
if [ -x voice-server/run_voice.sh ] && ! curl -s -m 2 http://127.0.0.1:9000/health >/dev/null 2>&1; then
  echo "Starting the Whisper voice server (log: data/voice-server.log)..."
  nohup voice-server/run_voice.sh > data/voice-server.log 2>&1 &
fi
[ -d build/classes ] || ./build.sh
exec "$JAVA_BIN/java" -Dfile.encoding=UTF-8 -cp "build/classes:lib/*" com.ptit.ecom.presentation.web.EcomApplication "$@"
