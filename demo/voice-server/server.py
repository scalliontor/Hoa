"""Self-hosted speech-to-text server of Họa.: receives audio, returns the transcript using Whisper.

This is the "Speech-to-Text" step of the voice-search flow in Assignment 06
(Microphone -> Audio -> Speech-to-Text -> Text Query -> Search Service). The Java application calls it through
WhisperClient (interface SpeechClient); the customer's audio never leaves the machine (NFR08).

API (see README.md):
    GET  /health                    -> {"ok": true, "model": ..., "device": ..., "compute_type": ...}
    POST /transcribe?language=en    -> {"text", "language", "duration", "seconds", "model"}
         language: "en" (default), "vi", or "auto" to let Whisper detect it.
Errors return 4xx/5xx with {"error": "..."}.
"""
import io
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from faster_whisper import WhisperModel

HOST = os.environ.get("VOICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("VOICE_PORT", "9000"))
MODEL_NAME = os.environ.get("VOICE_MODEL", "small")
COMPUTE_TYPE = os.environ.get("VOICE_COMPUTE_TYPE", "int8")
CPU_THREADS = int(os.environ.get("VOICE_CPU_THREADS", "8"))  # the 8 performance cores of the M2 Pro
DEFAULT_LANGUAGE = "en"
LANGUAGES = {"en", "vi", "auto"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per recording

# 1. Load the model once at start-up. CTranslate2 runs on the CPU on macOS; int8 is the fastest setting.
#    The first start downloads the model into the Hugging Face cache; later starts work offline.
print(f"Loading Whisper model '{MODEL_NAME}' ({COMPUTE_TYPE}, {CPU_THREADS} threads)...", flush=True)
model = WhisperModel(MODEL_NAME, device="cpu", compute_type=COMPUTE_TYPE, cpu_threads=CPU_THREADS)
# One transcription at a time; other requests (such as /health) are still answered in parallel.
model_lock = threading.Lock()


def transcribe(audio_bytes, language):
    """2. Transcribe: PyAV decodes any browser format (webm/opus, mp4/aac, wav, aiff) to 16 kHz mono."""
    started = time.perf_counter()
    with model_lock:
        segments, info = model.transcribe(io.BytesIO(audio_bytes), language=None if language == "auto" else language,
                                          beam_size=1, vad_filter=True, condition_on_previous_text=False)
        text = " ".join(segment.text.strip() for segment in segments).strip()
    return {"text": text, "language": info.language, "duration": round(info.duration, 2),
            "seconds": round(time.perf_counter() - started, 3), "model": MODEL_NAME}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path != "/health":
            return self.reply(404, {"error": "Unknown path"})
        self.reply(200, {"ok": True, "model": MODEL_NAME, "device": "cpu", "compute_type": COMPUTE_TYPE})

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/transcribe":
            return self.reply(404, {"error": "Unknown path"})
        # 3. Validate the request before running the model.
        language = parse_qs(url.query).get("language", [DEFAULT_LANGUAGE])[0]
        if language not in LANGUAGES:
            return self.reply(400, {"error": f"Unsupported language '{language}', use en, vi or auto"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return self.reply(400, {"error": "No audio in the request body"})
        if length > MAX_BYTES:
            return self.reply(413, {"error": "Audio is larger than 10 MB"})
        audio = self.rfile.read(length)
        # 4. Transcribe and answer with JSON; audio that cannot be decoded is the sender's error.
        try:
            result = transcribe(audio, language)
        except Exception as error:  # PyAV raises av.error.* for broken or non-audio data
            status = 400 if type(error).__module__.startswith("av") else 500
            return self.reply(status, {"error": f"Could not transcribe the audio: {error}"})
        self.reply(200, result)

    def reply(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[voice] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Voice server ready at http://{HOST}:{PORT} (model {MODEL_NAME})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
