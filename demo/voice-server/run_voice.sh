#!/usr/bin/env bash
# Start the self-hosted Whisper voice server on http://127.0.0.1:9000 (Chapters 3 and 5 of the report).
# First run: creates the venv, installs the libraries and downloads the model (needs Internet);
# later runs are fully offline. Override the model with VOICE_MODEL=base|small|large-v3-turbo.
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-$(command -v python3.12 || command -v python3)}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -r requirements.txt
fi
export VOICE_MODEL="${VOICE_MODEL:-small}"
export HF_HUB_DISABLE_XET=1   # plain HTTPS download; the Xet transfer stalled on this network
exec .venv/bin/python server.py
