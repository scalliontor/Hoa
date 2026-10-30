# voice-server — self-hosted Whisper for voice search

This folder is the **speech-to-text** part of Họa. In the Assignment 06 voice-search flow
(Microphone → Audio → Speech-to-Text → Text Query → Search Service) it turns the customer's recording into text.

- The Java application calls it through `WhisperClient` (implementation of the interface `SpeechClient`), used by
  `SpeechService.transcribe(audioInput)` — the class and method names of `tools/model.py` and the A06 slide.
- The transcript is shown to the customer, who can edit it before `QueryService.voiceQuery` runs the search.
- Report: **Chapter 3** (AI in e-commerce: why self-hosted, measured results) and **Chapter 5** (Code: how to run).
- No text-to-speech: the system listens, it does not talk back.

## Why self-hosted (NFR08)
1. **Privacy:** the customer's audio never leaves the machine; only the recognised text enters the system.
2. **Offline:** after the first model download, recognition needs no Internet (only Gemma 4 does).
3. **Measured quality and speed:** the model is chosen by measurements on the demo laptop (see "Model choice").

## Start
```bash
./run_voice.sh                       # first run creates .venv, installs faster-whisper, downloads the model
VOICE_MODEL=base ./run_voice.sh      # pick another model
```
The server listens on `http://127.0.0.1:9000`. The demo's `../run.sh` calls `../voice-server/run_voice.sh`.
If the server is down, `SpeechService.transcribe` returns null and the UI asks the customer to type instead.

## API
| Method | Path | Input | Output |
|---|---|---|---|
| GET | `/health` | — | `{"ok": true, "model": "small", "device": "cpu", "compute_type": "int8"}` |
| POST | `/transcribe?language=en` | raw audio bytes: `audio/webm` (Opus, Chrome MediaRecorder), `audio/mp4` (AAC, Safari), `audio/wav`, `audio/aiff`; at most 10 MB | `{"text": "...", "language": "en", "duration": 2.5, "seconds": 0.6, "model": "small"}` |

`language` is `en` (default, the product language), `vi`, or `auto` (Whisper detects the language).
Errors: `400` (missing or undecodable audio, unsupported language), `404` (unknown path), `413` (over 10 MB),
`500` (recognition failure), always with `{"error": "..."}`.

Example:
```bash
curl -s --data-binary @samples/en/e02.aiff -H "Content-Type: audio/aiff" \
     "http://127.0.0.1:9000/transcribe?language=en"
```

## Model choice
Measured on the demo laptop (Apple M2 Pro, 8 performance + 4 efficiency cores, 32 GB), faster-whisper 1.2.1,
CTranslate2 on CPU with `int8`, greedy decoding (`beam_size=1`), VAD filter on; 20 English utterances
(mean 2.1 s of audio) and 18 Vietnamese utterances (mean 2.4 s). Source: `../../build/eval/voice_model_bench.json`.

| Model (size) | Language | Mean time | Max time | WER | CER | Exact sentences |
|---|---|---|---|---|---|---|
| `base` (145 MB) | English | 0.26 s | 0.35 s | 6.0% | 2.0% | 15/20 |
| **`small` (484 MB)** | **English** | **0.71 s** | **0.90 s** | **2.0%** | **0.9%** | **18/20** |
| `base` | Vietnamese | 0.33 s | 0.61 s | 43.5% | 22.6% | 1/18 |
| `small` | Vietnamese | 0.78 s | 0.89 s | 22.6% | 9.2% | 3/18 |

**Chosen: `small`, 8 CPU threads.** It has the best English accuracy we could measure (the two remaining errors are
"Klimt" → "Climbed" and "paintings" → "painting") and transcribes a 2–4 s query in under 1 s, far inside
NFR08 (≤ 3 s for a 5 s sentence). `base` is 2.7× faster but makes three times as many word errors, mostly on
artist names (Hokusai → "Hocus-I", Klimt → "flimped").
- Threads: 8 (the performance cores) gave 0.70 s mean, against 0.89 s with 12 threads and 1.00 s with 4.
- `large-v3-turbo` (1.6 GB) was planned but not measured: its download stalled at about 0.1 MB/s on the shared
  network. To try it later: `.venv/bin/python bench_models.py --lang en large-v3-turbo`, then
  `VOICE_MODEL=large-v3-turbo ./run_voice.sh` if it stays within NFR08.
- A vocabulary hint (Whisper `hotwords` / `initial_prompt` with the artist names) fixed "Klimt" but introduced a new
  error on another sentence and added latency, so it is not used.
- Vietnamese stays a secondary option (`language=vi`): `small` reaches 22.6% WER, and `language=auto` with
  `small` misdetected a Vietnamese sentence as Chinese — callers should pass the language explicitly.

## Evaluation
`eval_voice.py` synthesises 20 English test utterances with the macOS voices Samantha (US), Daniel (UK) and
Karen (AU) — the demo queries plus other painting-shop queries (Van Gogh, Hokusai, Klimt, colours, "under 150
dollars", order codes spoken digit by digit) — converts some of them to WAV, M4A (AAC) and WebM (Opus), sends them
to the running server and computes WER/CER and latency. A Vietnamese set (voice Linh) is kept as a secondary table.
```bash
./run_voice.sh &                              # start the server
.venv/bin/python eval_voice.py                # English (primary)
.venv/bin/python eval_voice.py --lang vi      # Vietnamese (secondary)
.venv/bin/python bench_models.py --lang en base small large-v3-turbo   # model comparison
```
Results: `../../build/eval/voice_eval.txt`, `voice_eval.json` and `voice_model_bench.json`.
Limitation: synthetic voices are cleaner than a real customer in a noisy room, so the numbers are an upper bound.

## Files
| File | Role |
|---|---|
| `server.py` | HTTP server: `/health`, `/transcribe` (loads the model once, one transcription at a time) |
| `run_voice.sh` | Creates the venv, installs the libraries, starts the server |
| `requirements.txt` | Python dependency (faster-whisper; its PyAV dependency decodes audio, no ffmpeg needed) |
| `eval_voice.py` | Synthesises the test utterances and evaluates the running server over HTTP |
| `bench_models.py` | Compares Whisper models to choose the server model |
| `samples/en`, `samples/vi` | Test recordings (e01–e20, q01–q18); the demo can replay them |
