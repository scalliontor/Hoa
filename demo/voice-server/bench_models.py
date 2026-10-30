"""Compare Whisper models on the test utterances to choose the server model (README, "Model choice").

Run: .venv/bin/python bench_models.py --lang en base small large-v3-turbo
Writes tieuluan/build/eval/voice_model_bench.json (one entry per language and model).
"""
import argparse
import json
import statistics
import time

from faster_whisper import WhisperModel

import eval_voice


def bench(name, lang, threads, compute_type="int8"):
    started = time.perf_counter()
    model = WhisperModel(name, device="cpu", compute_type=compute_type, cpu_threads=threads)
    load = time.perf_counter() - started
    rows = []
    for sid, _spoken, reference, _voice in eval_voice.SETS[lang]:
        path = eval_voice.SAMPLES_DIR / lang / f"{sid}.aiff"
        started = time.perf_counter()
        segments, info = model.transcribe(str(path), language=lang, beam_size=1, vad_filter=True,
                                          condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segments).strip()
        seconds = time.perf_counter() - started
        wer, cer = eval_voice.error_rates(reference, text, lang)
        rows.append({"id": sid, "seconds": round(seconds, 3), "duration": round(info.duration, 2),
                     "wer": round(wer, 4), "cer": round(cer, 4), "reference": reference, "text": text})
    words = [len(eval_voice.normalize(r["reference"], lang)) for r in rows]
    return {"language": lang, "model": name, "compute_type": compute_type, "cpu_threads": threads,
            "load_seconds": round(load, 1),
            "mean_seconds": round(statistics.mean(r["seconds"] for r in rows), 3),
            "max_seconds": round(max(r["seconds"] for r in rows), 3),
            "mean_duration": round(statistics.mean(r["duration"] for r in rows), 2),
            "wer": round(sum(r["wer"] * w for r, w in zip(rows, words)) / sum(words), 4),
            "cer": round(statistics.mean(r["cer"] for r in rows), 4),
            "exact": sum(r["wer"] == 0 for r in rows), "n": len(rows), "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=sorted(eval_voice.SETS), default="en")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("models", nargs="*", default=["base", "small", "large-v3-turbo"])
    args = parser.parse_args()
    out = eval_voice.EVAL_DIR / "voice_model_bench.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(out.read_text()) if out.exists() else {}
    for name in args.models:
        result = bench(name, args.lang, args.threads)
        data[f"{args.lang}/{name}"] = result
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False), flush=True)
