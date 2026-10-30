"""Evaluate the voice server: synthesise test utterances with macOS voices, POST them to /transcribe,
measure WER/CER and latency.

Run (the server must be listening on 127.0.0.1:9000):
    .venv/bin/python eval_voice.py            # English set (primary)
    .venv/bin/python eval_voice.py --lang vi  # Vietnamese set (secondary table)
Results go to tieuluan/build/eval/voice_eval.json and voice_eval.txt (used in Chapters 3 and 5).
"""
import argparse
import json
import re
import statistics
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES_DIR = HERE / "samples"
EVAL_DIR = HERE.parents[1] / "build" / "eval"
SERVER = "http://127.0.0.1:9000"

# (id, text spoken by the macOS voice, reference transcript, voice). Order codes are read digit by digit,
# prices in words, the way a customer says them. Queries e01-e05 are model.DEMO_QUERIES.
SAMPLES_EN = [
    ("e01", "blue landscape paintings", "blue landscape paintings", "Samantha"),
    ("e02", "Monet paintings under one hundred dollars", "Monet paintings under 100 dollars", "Daniel"),
    ("e03", "show me paintings similar to this image", "show me paintings similar to this image", "Karen"),
    ("e04", "find my order two zero two six one zero zero one", "find my order 20261001", "Samantha"),
    ("e05", "where is my latest order?", "where is my latest order", "Daniel"),
    ("e06", "Van Gogh sunflowers", "Van Gogh sunflowers", "Karen"),
    ("e07", "The Great Wave by Hokusai", "the Great Wave by Hokusai", "Samantha"),
    ("e08", "Klimt paintings with gold", "Klimt paintings with gold", "Daniel"),
    ("e09", "a red abstract painting for the living room", "a red abstract painting for the living room", "Karen"),
    ("e10", "yellow still life with fruit", "yellow still life with fruit", "Samantha"),
    ("e11", "impressionist paintings under one hundred and fifty dollars",
     "impressionist paintings under 150 dollars", "Daniel"),
    ("e12", "a black oak frame", "a black oak frame", "Karen"),
    ("e13", "winter landscape with snow", "winter landscape with snow", "Samantha"),
    ("e14", "Japanese woodblock print of Mount Fuji", "Japanese woodblock print of Mount Fuji", "Daniel"),
    ("e15", "The Starry Night", "the Starry Night", "Karen"),
    ("e16", "a large painting for my bedroom", "a large painting for my bedroom", "Samantha"),
    ("e17", "cancel order two zero two six one zero zero three", "cancel order 20261003", "Daniel"),
    ("e18", "sunset over the sea", "sunset over the sea", "Karen"),
    ("e19", "portrait of a woman in a blue dress", "portrait of a woman in a blue dress", "Samantha"),
    ("e20", "what is the status of my last order", "what is the status of my last order", "Daniel"),
]
# Secondary Vietnamese set (voice "Linh"), kept from the first measurement round.
SAMPLES_VI = [
    ("q01", "tranh phong cảnh tông xanh", "tranh phong cảnh tông xanh", "Linh"),
    ("q02", "tranh của Monet dưới hai triệu", "tranh của Monet dưới 2 triệu", "Linh"),
    ("q03", "tìm tranh giống ảnh này", "tìm tranh giống ảnh này", "Linh"),
    ("q04", "tìm đơn hai không hai sáu một không không một của tôi", "tìm đơn 20261001 của tôi", "Linh"),
    ("q05", "đơn mới nhất của tôi đang ở đâu", "đơn mới nhất của tôi đang ở đâu", "Linh"),
    ("q06", "tranh hoa hướng dương của Van Gogh", "tranh hoa hướng dương của Van Gogh", "Linh"),
    ("q07", "sóng lớn ngoài khơi Kanagawa của Hokusai", "sóng lớn ngoài khơi Kanagawa của Hokusai", "Linh"),
    ("q08", "tranh trừu tượng màu đỏ cho phòng khách", "tranh trừu tượng màu đỏ cho phòng khách", "Linh"),
    ("q09", "tranh tĩnh vật hoa quả màu vàng", "tranh tĩnh vật hoa quả màu vàng", "Linh"),
    ("q10", "tranh chân dung thiếu nữ", "tranh chân dung thiếu nữ", "Linh"),
    ("q11", "cho tôi xem tranh trường phái ấn tượng dưới một triệu",
     "cho tôi xem tranh trường phái ấn tượng dưới 1 triệu", "Linh"),
    ("q12", "khung gỗ sồi màu đen", "khung gỗ sồi màu đen", "Linh"),
    ("q13", "tranh phong cảnh mùa đông có tuyết", "tranh phong cảnh mùa đông có tuyết", "Linh"),
    ("q14", "tranh Nhật Bản vẽ núi Phú Sĩ", "tranh Nhật Bản vẽ núi Phú Sĩ", "Linh"),
    ("q15", "tranh đêm đầy sao", "tranh đêm đầy sao", "Linh"),
    ("q16", "tôi muốn mua tranh khổ lớn treo phòng ngủ", "tôi muốn mua tranh khổ lớn treo phòng ngủ", "Linh"),
    ("q17", "hủy đơn hai không hai sáu một không không ba", "hủy đơn 20261003", "Linh"),
    ("q18", "tranh biển xanh lúc hoàng hôn", "tranh biển xanh lúc hoàng hôn", "Linh"),
]
SETS = {"en": SAMPLES_EN, "vi": SAMPLES_VI}
# A few utterances are also sent in the formats browsers produce (Chrome: WebM/Opus, Safari: MP4/AAC).
EXTRA_FORMATS = {"e01": ["wav", "m4a", "webm"], "e04": ["webm"], "e07": ["m4a"], "e15": ["wav"],
                 "q01": ["wav", "m4a", "webm"], "q04": ["webm"], "q07": ["m4a"], "q15": ["wav"]}
CONTENT_TYPES = {".aiff": "audio/aiff", ".wav": "audio/wav", ".m4a": "audio/mp4", ".webm": "audio/webm"}


# ------------------------------------------------------------------ samples
def make_samples(lang):
    """Synthesise AIFF files with `say`, then convert some of them to WAV, M4A (AAC) and WebM (Opus)."""
    folder = SAMPLES_DIR / lang
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for sid, spoken, reference, voice in SETS[lang]:
        aiff = folder / f"{sid}.aiff"
        if not aiff.exists():
            subprocess.run(["say", "-v", voice, "-o", str(aiff), spoken], check=True)
        files.append((sid, aiff, reference))
        for fmt in EXTRA_FORMATS.get(sid, []):
            target = folder / f"{sid}.{fmt}"
            if not target.exists():
                convert(aiff, target, fmt)
            files.append((sid, target, reference))
    return files


def convert(source, target, fmt):
    if fmt == "wav":
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", str(source), str(target)], check=True)
    elif fmt == "m4a":
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(source), str(target)], check=True)
    elif fmt == "webm":
        to_webm_opus(source, target)


def to_webm_opus(source, target):
    """WebM/Opus like Chrome's MediaRecorder, encoded with PyAV from the venv (no ffmpeg binary needed)."""
    import av
    from av.audio.resampler import AudioResampler
    with av.open(str(source)) as inp, av.open(str(target), "w", format="webm") as out:
        stream = out.add_stream("libopus", rate=48000)
        stream.layout = "mono"
        resampler = AudioResampler(format="s16", layout="mono", rate=48000)
        for frame in inp.decode(audio=0):
            for resampled in resampler.resample(frame):
                for packet in stream.encode(resampled):
                    out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)


# ------------------------------------------------------------------ scoring
UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i > 1}
VI_DIGITS = {"không": "0", "một": "1", "mốt": "1", "hai": "2", "ba": "3", "bốn": "4", "tư": "4", "năm": "5",
             "lăm": "5", "sáu": "6", "bảy": "7", "tám": "8", "chín": "9"}


def english_numbers(words):
    """'one hundred and fifty' -> '150'; a run of single digits ('two zero two six') -> '2026' (order codes)."""
    out, run = [], []

    def flush():
        if not run:
            return
        if len(run) > 1 and all(w in UNITS and UNITS[w] < 10 for w in run):
            out.append("".join(str(UNITS[w]) for w in run))
        else:
            total, current = 0, 0
            for w in run:
                if w in UNITS:
                    current += UNITS[w]
                elif w in TENS:
                    current += TENS[w]
                elif w == "hundred":
                    current *= 100
                elif w == "thousand":
                    total, current = total + current * 1000, 0
            out.append(str(total + current))
        run.clear()

    for i, w in enumerate(words):
        is_number = w in UNITS or w in TENS or w in ("hundred", "thousand")
        # "and" only belongs to a number between two number words ("one hundred and fifty")
        joins = w == "and" and run and i + 1 < len(words) and (words[i + 1] in UNITS or words[i + 1] in TENS)
        if is_number:
            run.append(w)
        elif not joins:
            flush()
            out.append(w)
    flush()
    return out


def normalize(text, lang="en"):
    """Lower case, drop punctuation, spell prices and order codes the same way in reference and hypothesis."""
    text = text.lower()
    text = re.sub(r"\$\s*(\d[\d,]*)", r"\1 dollars", text)         # "$100" -> "100 dollars"
    text = re.sub(r"(?<=\d)[,\-\s](?=\d)", "", text)                # "2026-1001", "20,261,001" -> one number
    words = re.sub(r"[^\w\s]", " ", text).split()
    if lang == "vi":
        words = [VI_DIGITS.get(w, w) for w in words]
    else:
        words = english_numbers(words)
    merged = []
    for w in words:                                                 # digits spoken one by one -> one code
        if w.isdigit() and merged and merged[-1].isdigit() and len(w) == 1:
            merged[-1] += w
        else:
            merged.append(w)
    return merged


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def error_rates(reference, hypothesis, lang="en"):
    ref, hyp = normalize(reference, lang), normalize(hypothesis, lang)
    wer = edit_distance(ref, hyp) / max(1, len(ref))
    ref_chars, hyp_chars = list(" ".join(ref)), list(" ".join(hyp))
    cer = edit_distance(ref_chars, hyp_chars) / max(1, len(ref_chars))
    return wer, cer


# ------------------------------------------------------------------ run
def transcribe(path, lang):
    request = urllib.request.Request(f"{SERVER}/transcribe?language={lang}", data=path.read_bytes(), method="POST",
                                     headers={"Content-Type": CONTENT_TYPES[path.suffix]})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        body = json.load(response)
    body["round_trip"] = round(time.perf_counter() - started, 3)
    return body


def evaluate(lang):
    files = make_samples(lang)
    with urllib.request.urlopen(f"{SERVER}/health", timeout=10) as response:
        health = json.load(response)
    rows = []
    for sid, path, reference in files:
        result = transcribe(path, lang)
        wer, cer = error_rates(reference, result["text"], lang)
        rows.append({"id": sid, "file": f"{lang}/{path.name}", "format": path.suffix[1:], "reference": reference,
                     "text": result["text"], "duration": result["duration"], "seconds": result["seconds"],
                     "round_trip": result["round_trip"], "wer": round(wer, 4), "cer": round(cer, 4),
                     "exact": wer == 0})
        print(f"{lang}/{path.name:10} {result['seconds']:5.2f}s WER={wer:.2f} | {result['text']}")
    main_rows = [r for r in rows if r["format"] == "aiff"]
    words = sum(len(normalize(r["reference"], lang)) for r in main_rows)
    summary = {
        "language": lang, "model": health.get("model"), "device": health.get("device"),
        "compute_type": health.get("compute_type"), "n_utterances": len(main_rows), "n_requests": len(rows),
        "voices": sorted({v for *_, v in SETS[lang]}), "formats": sorted({r["format"] for r in rows}),
        "mean_seconds": round(statistics.mean(r["seconds"] for r in rows), 3),
        "max_seconds": round(max(r["seconds"] for r in rows), 3),
        "mean_audio_duration": round(statistics.mean(r["duration"] for r in main_rows), 2),
        "max_audio_duration": round(max(r["duration"] for r in main_rows), 2),
        "wer": round(sum(r["wer"] * len(normalize(r["reference"], lang)) for r in main_rows) / words, 4),
        "cer": round(statistics.mean(r["cer"] for r in main_rows), 4),
        "exact_sentences": sum(r["exact"] for r in main_rows),
        "nfr08_met": all(r["seconds"] <= 3.0 for r in rows),
    }
    return {"summary": summary, "results": rows}


def report_lines(section, title):
    s = section["summary"]
    lines = [
        title,
        f"  Model: {s['model']} | device: {s['device']} ({s['compute_type']}) | language={s['language']}",
        f"  Test set: {s['n_utterances']} utterances spoken by macOS voices {', '.join(s['voices'])}; "
        f"{s['n_requests']} requests in formats {', '.join(s['formats'])}",
        f"  Audio length: mean {s['mean_audio_duration']} s, max {s['max_audio_duration']} s",
        f"  Transcription time: mean {s['mean_seconds']} s, max {s['max_seconds']} s "
        f"(NFR08 <= 3 s: {'met' if s['nfr08_met'] else 'NOT met'})",
        f"  WER {s['wer'] * 100:.1f}% | CER {s['cer'] * 100:.1f}% | exact sentences "
        f"{s['exact_sentences']}/{s['n_utterances']}",
        "  Worst sentences:",
    ]
    wrong = [r for r in section["results"] if r["format"] == "aiff" and r["wer"] > 0]
    for r in sorted(wrong, key=lambda r: (-r["wer"], -r["cer"]))[:5]:
        lines.append(f"    {r['id']}: \"{r['reference']}\" -> \"{r['text']}\" (WER {r['wer'] * 100:.0f}%)")
    if not wrong:
        lines.append("    none")
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=sorted(SETS), default="en")
    lang = parser.parse_args().lang
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_json = EVAL_DIR / "voice_eval.json"
    data = json.loads(out_json.read_text()) if out_json.exists() else {}
    data[lang] = evaluate(lang)
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    lines = ["Voice recognition evaluation (self-hosted Whisper, demo/voice-server)"]
    if "en" in data:
        lines += report_lines(data["en"], "English (primary - the product language)")
    if "vi" in data:
        lines += report_lines(data["vi"], "Vietnamese (secondary)")
    lines.append("Note: synthetic voices are cleaner than a real customer in a noisy room, so these numbers are an "
                 "upper bound; the live demo uses a real microphone.")
    (EVAL_DIR / "voice_eval.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
