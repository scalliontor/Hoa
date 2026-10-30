"""Experimental evaluation of the Họa. demo in the style of slide A06 (results for Chapters 3 and 5).

Starts two copies of the shop on fresh databases — one with Gemma 4, one with Gemma unreachable (the NFR02
fallbacks) — and measures through the HTTP API:
  text search    14 direct + 6 paraphrased requests, relevance judged from the catalogue attributes
  voice search   the self-hosted Whisper transcripts of the recorded requests (voice-server/samples/en)
  image search   8 photos of catalogue paintings that differ from the shop images (data/eval_images)
  assistant      7 order and search questions, including another customer's order (NFR01)
  room picks     the 3 sample rooms of "Try it in your room" (UC14)
Writes ../build/eval/eval_results.json, eval_summary.txt and eval_tables.tex.

Usage (from demo/, after ./build.sh, with the voice server running): python3 scripts/evaluate.py
"""
import base64
import json
import re
import statistics
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1]
OUT = DEMO.parent / "build" / "eval"
JAVA = subprocess.run([str(DEMO / "scripts" / "java_home.sh")], capture_output=True, text=True).stdout.strip()
CATALOG = json.loads((DEMO / "data" / "catalog.json").read_text())
PAINTINGS = {p["productId"]: p for p in CATALOG["paintings"]}
SAMPLES = DEMO / "voice-server" / "samples" / "en"


def where(**rule):
    """Relevant paintings: every given attribute is equal (artist: part of the name; max_price: upper limit)."""
    found = set()
    for pid, p in PAINTINGS.items():
        ok = all(v.lower() in p["artist"].lower() if k == "artist" else str(p[k]).lower() == str(v).lower()
                 for k, v in rule.items() if k != "max_price")
        if ok and p["price"] <= rule.get("max_price", 10 ** 6):
            found.add(pid)
    return found


# (sample id or None, request, relevant product ids). Sample ids point to the Whisper recordings.
SEARCHES = [
    ("e01", "blue landscape paintings", where(subject="landscape", dominantColor="blue")),
    ("e02", "Monet paintings under 100 dollars", where(artist="Monet", max_price=100)),
    ("e06", "Van Gogh sunflowers", {"P06"}),
    ("e07", "the Great Wave by Hokusai", {"P10"}),
    ("e08", "Klimt paintings with gold", where(artist="Klimt")),
    ("e09", "a red abstract painting for the living room", {"P26"}),
    ("e10", "yellow still life with fruit", where(subject="still life")),
    ("e11", "impressionist paintings under 150 dollars", where(style="Impressionism", max_price=150)),
    ("e14", "Japanese woodblock print of Mount Fuji", {"P11"}),
    ("e15", "the Starry Night", {"P05"}),
    ("e18", "sunset over the sea", where(subject="seascape")),
    ("e19", "portrait of a woman in a blue dress", where(subject="portrait")),
    (None, "green landscape under 100 dollars", where(subject="landscape", dominantColor="green", max_price=100)),
    (None, "Japanese prints of the sea", where(style="Ukiyo-e", subject="seascape")),
]
# Paraphrased requests: no style, subject or colour word that the keyword rules know.
PARAPHRASES = [
    (None, "a painting of a mountain in Provence", {"P22"}),
    (None, "artworks by the Dutch master of light", where(artist="Vermeer")),
    (None, "flower paintings under a hundred bucks", where(subject="flowers", max_price=100)),
    (None, "something from Tahiti", {"P24"}),
    (None, "the painter of The Scream", {"P25"}),
    (None, "a night sky full of stars", {"P05"}),
]
# (account, question, words the answer must contain, expected tool, words that must never appear)
OTHER_ORDER = ["Tran", "Binh", "172", "Composition VII", "Ha Dong", "96A"]
QUESTIONS = [
    ("C001", "find my order 20261001", ["20261001", "ship"], "find_order", []),
    ("C001", "where is my latest order?", ["20261001"], "latest_order", []),
    ("C002", "where is my latest order?", ["20261003"], "latest_order", []),
    ("C001", "find my order 20261003", ["not found|n't find|could not|cannot find|no order"], "find_order",
     OTHER_ORDER),
    ("C001", "list my orders", ["20261001", "20261002"], "list_orders", OTHER_ORDER),
    ("C002", "what is the status of my last order", ["20261003", "placed|prepar"], "latest_order", []),
    ("C001", "Monet paintings under 100 dollars", ["Impression, Sunrise|Water Lilies|Woman with a Parasol"],
     "search_paintings", []),
]
VOICE_ORDERS = [("e04", "find my order 20261001"), ("e05", "where is my latest order"),
                ("e17", "cancel order 20261003"), ("e20", "what is the status of my last order")]
ROOM_WORDS = ["sofa", "couch", "wall", "light", "floor", "window", "wood", "brick", "cushion", "rug", "chair",
              "table", "plant", "seating", "armchair", "shelf", "lamp", "curtain", "bed"]


class Shop:
    """One running copy of the demo with its own config and database."""

    def __init__(self, name, port, gemma_online, folder):
        config = (DEMO / "config" / "app.properties").read_text()
        config = re.sub(r"server.port=\d+", f"server.port={port}", config)
        config = re.sub(r"db.path=.*", f"db.path={folder}/{name}.db", config)
        if not gemma_online:
            config = re.sub(r"gemma.baseUrl=.*", "gemma.baseUrl=http://127.0.0.1:9/llm/v1/", config)
        path = Path(folder) / f"{name}.properties"
        path.write_text(config)
        self.name, self.base, self.cookies = name, f"http://127.0.0.1:{port}", {}
        self.process = subprocess.Popen([f"{JAVA}/java", "-Dfile.encoding=UTF-8", "-cp", "build/classes:lib/*",
                                         "com.ptit.ecom.presentation.web.EcomApplication", str(path)],
                                        cwd=DEMO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        for _ in range(60):
            try:
                self.call("GET", "/api/session")
                break
            except OSError:
                time.sleep(0.5)

    def call(self, method, path, body=None, raw=None, account=None):
        headers = {"Content-Type": "application/json" if raw is None else "application/octet-stream"}
        if account:
            if account not in self.cookies:
                request = urllib.request.Request(self.base + "/api/login", method="POST", headers=headers,
                                                 data=json.dumps({"customerId": account}).encode())
                with urllib.request.urlopen(request) as response:
                    self.cookies[account] = response.headers["Set-Cookie"].split(";")[0]
            headers["Cookie"] = self.cookies[account]
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as error:
            result = json.loads(error.read() or b"{}")
        return result, round(time.time() - started, 2)

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=10)


def image(path):
    return "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def ranking_metrics(ids, relevant):
    """Hit@1, precision in the top 5 (out of min(5, |relevant|)) and reciprocal rank."""
    top = ids[:5]
    first = next((i + 1 for i, pid in enumerate(ids) if pid in relevant), None)
    return {"hit1": int(bool(ids) and ids[0] in relevant),
            "p5": round(len([p for p in top if p in relevant]) / min(5, len(relevant)), 3),
            "rr": round(1 / first, 3) if first else 0.0}


def words(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower().replace("$", "")).split()


def wer(reference, hypothesis):
    ref, hyp = words(reference), words(hypothesis)
    distance = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        previous, distance[0] = distance[0], i
        for j, h in enumerate(hyp, 1):
            previous, distance[j] = distance[j], min(distance[j] + 1, distance[j - 1] + 1, previous + (r != h))
    return distance[len(hyp)] / max(1, len(ref))


def search_runs(shop, runs, label):
    rows = []
    for group, requests in (("direct", SEARCHES), ("paraphrased", PARAPHRASES)):
        for sample, text, relevant in requests:
            results, seconds = shop.call("GET", "/api/search?q=" + urllib.request.quote(text))
            ids = [r["product"]["productId"] for r in results]
            rows.append({"mode": label, "group": group, "request": text, "relevant": sorted(relevant), "top5": ids[:5],
                         "reason": results[0]["reason"] if results else "", "seconds": seconds,
                         **ranking_metrics(ids, relevant)})
    runs.extend(rows)
    return rows


def voice_runs(shop):
    rows = []
    for sample, reference, relevant in [(s, t, r) for s, t, r in SEARCHES if s] + \
                                        [(s, t, None) for s, t in VOICE_ORDERS]:
        audio = (SAMPLES / f"{sample}.aiff").read_bytes()
        heard, transcribe_seconds = shop.call("POST", "/api/voice/transcribe", raw=audio)
        transcript = heard.get("transcript", "")
        row = {"sample": sample, "reference": reference, "transcript": transcript,
               "wer": round(wer(reference, transcript), 3), "transcribe_seconds": transcribe_seconds}
        if relevant is not None:
            results, seconds = shop.call("POST", "/api/search/voice", {"transcript": transcript})
            ids = [r["product"]["productId"] for r in results]
            row.update({"relevant": sorted(relevant), "top5": ids[:5], "search_seconds": seconds,
                        **ranking_metrics(ids, relevant)})
        else:
            row["order_number_kept"] = all(n in transcript for n in re.findall(r"\d{8}", reference))
        rows.append(row)
    return rows


def image_runs(shop, label):
    rows = []
    for case in json.loads((DEMO / "data" / "eval_images.json").read_text()):
        results, seconds = shop.call("POST", "/api/search/image", {"image": image(DEMO / case["image"])})
        ids = [r["product"]["productId"] for r in results]
        rank = ids.index(case["expected"]) + 1 if case["expected"] in ids else None
        rows.append({"mode": label, "query": case["queryId"], "expected": case["expected"], "top3": ids[:3],
                     "rank": rank, "hit1": int(rank == 1), "hit3": int(bool(rank) and rank <= 3),
                     "rr": round(1 / rank, 3) if rank else 0.0, "seconds": seconds,
                     "reason": results[0]["reason"] if results else ""})
    return rows


def assistant_runs(shop, label):
    rows = []
    for account, question, expected, tool, forbidden in QUESTIONS:
        reply, seconds = shop.call("POST", "/api/assistant", {"message": question}, account=account)
        answer = reply.get("answer", "")
        correct = all(re.search(e, answer, re.I) for e in expected)
        leaks = [w for w in forbidden if re.search(rf"\b{re.escape(w)}\b", answer, re.I)]
        rows.append({"mode": label, "account": account, "question": question, "answer": answer,
                     "tools": reply.get("toolsUsed", []), "tool_ok": tool in reply.get("toolsUsed", []),
                     "correct": correct, "leaks": leaks, "ai": reply.get("aiUsed"), "seconds": seconds})
    return rows


def room_runs(shop, label):
    rows = []
    for room in json.loads((DEMO / "web" / "img" / "rooms" / "rooms.json").read_text()):
        photo = image(DEMO / "web" / room["imageUrl"].lstrip("/"))
        reading, describe_seconds = shop.call("POST", "/api/room/describe", {"image": photo})
        picks, search_seconds = shop.call("POST", "/api/room/search", {"image": photo})
        checked = []
        room_clues = ROOM_WORDS + [w for key in ("colors", "tone", "light", "interior", "mood")
                                   for w in re.split(r"[,\s]+", (reading.get(key) or "").lower()) if len(w) > 2]
        for pick in picks:
            p = PAINTINGS[pick["product"]["productId"]]
            text = pick["reason"].lower()
            count = len(pick["reason"].split())
            painting_clue = any(c.lower() in text for c in
                                [p["dominantColor"], p["subject"].split()[0], p["style"][:6], p["artist"].split()[-1]])
            room_clue = any(w in text for w in room_clues)
            checked.append({"productId": p["productId"], "reason": pick["reason"], "words": count,
                            "length_ok": 15 <= count <= 25, "concrete": painting_clue and room_clue})
        rows.append({"mode": label, "room": room["roomId"], "reading": {k: reading.get(k) for k in
                     ("ai", "room", "style", "subject", "color", "mood", "light")},
                     "describe_seconds": describe_seconds, "search_seconds": search_seconds,
                     "picks": checked})
    return rows


def mean(values):
    values = list(values)
    return round(statistics.mean(values), 3) if values else 0.0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        online = Shop("online", 8701, True, folder)
        offline = Shop("offline", 8702, False, folder)
        try:
            text = []
            search_runs(online, text, "Gemma 4")
            search_runs(offline, text, "keyword rules")
            voice = voice_runs(online)
            images = image_runs(online, "Gemma 4 vision") + image_runs(offline, "local colour")
            orders = assistant_runs(online, "Gemma 4 tools") + assistant_runs(offline, "rules")
            rooms = room_runs(online, "Gemma 4") + room_runs(offline, "vector fallback")
        finally:
            online.stop()
            offline.stop()
    summary = summarise(text, voice, images, orders, rooms)
    (OUT / "eval_results.json").write_text(json.dumps(
        {"date": time.strftime("%Y-%m-%d %H:%M"), "summary": summary, "text": text, "voice": voice,
         "image": images, "assistant": orders, "room": rooms}, ensure_ascii=False, indent=2))
    write_summary(summary, text, voice, images, orders, rooms)
    write_tex(summary)
    print((OUT / "eval_summary.txt").read_text())


def summarise(text, voice, images, orders, rooms):
    s = {}
    for mode in ("Gemma 4", "keyword rules"):
        for group in ("direct", "paraphrased"):
            rows = [r for r in text if r["mode"] == mode and r["group"] == group]
            s[f"text/{mode}/{group}"] = {"n": len(rows), "hit1": mean(r["hit1"] for r in rows),
                                         "p5": mean(r["p5"] for r in rows), "mrr": mean(r["rr"] for r in rows),
                                         "seconds": mean(r["seconds"] for r in rows)}
    searched = [r for r in voice if "hit1" in r]
    s["voice/Whisper + Gemma 4"] = {"n": len(searched), "hit1": mean(r["hit1"] for r in searched),
                                    "p5": mean(r["p5"] for r in searched), "mrr": mean(r["rr"] for r in searched),
                                    "seconds": mean(r["transcribe_seconds"] + r["search_seconds"] for r in searched),
                                    "wer": mean(r["wer"] for r in voice), "utterances": len(voice),
                                    "transcribe_seconds": mean(r["transcribe_seconds"] for r in voice),
                                    "order_numbers_kept": sum(r.get("order_number_kept", False) for r in voice)}
    for mode in ("Gemma 4 vision", "local colour"):
        rows = [r for r in images if r["mode"] == mode]
        s[f"image/{mode}"] = {"n": len(rows), "hit1": mean(r["hit1"] for r in rows), "hit3": mean(r["hit3"] for r in rows),
                              "mrr": mean(r["rr"] for r in rows), "seconds": mean(r["seconds"] for r in rows)}
    for mode in ("Gemma 4 tools", "rules"):
        rows = [r for r in orders if r["mode"] == mode]
        s[f"assistant/{mode}"] = {"n": len(rows), "correct": sum(r["correct"] for r in rows),
                                  "tool_ok": sum(r["tool_ok"] for r in rows),
                                  "leaks": sum(len(r["leaks"]) for r in rows), "seconds": mean(r["seconds"] for r in rows)}
    for mode in ("Gemma 4", "vector fallback"):
        rows = [r for r in rooms if r["mode"] == mode]
        picks = [p for r in rows for p in r["picks"]]
        s[f"room/{mode}"] = {"rooms": len(rows), "picks": len(picks),
                             "non_empty": sum(bool(r["picks"]) for r in rows),
                             "reasons_present": sum(bool(p["reason"]) for p in picks),
                             "length_ok": sum(p["length_ok"] for p in picks),
                             "concrete": sum(p["concrete"] for p in picks),
                             "seconds": mean(r["describe_seconds"] + r["search_seconds"] for r in rows)}
    return s


def write_summary(s, text, voice, images, orders, rooms):
    lines = [f"Họa. demo — experimental evaluation ({time.strftime('%Y-%m-%d %H:%M')})",
             "Two copies of the shop on fresh databases: Gemma 4 online, and Gemma 4 unreachable (NFR02 fallbacks).",
             "Relevance of a search result is judged from the catalogue attributes (data/catalog.json).",
             "Hit@1 = top result relevant; P@5 = relevant results in the top 5 / min(5, relevant);"
             " MRR = mean reciprocal rank.", "",
             "1. Search", f"{'Input':<34}{'n':>3}{'Hit@1':>8}{'P@5':>8}{'MRR':>8}{'s/query':>9}"]
    for key, label in (("text/Gemma 4/direct", "Text, Gemma 4"),
                       ("text/keyword rules/direct", "Text, keyword rules (offline)"),
                       ("text/Gemma 4/paraphrased", "Paraphrased text, Gemma 4"),
                       ("text/keyword rules/paraphrased", "Paraphrased text, keyword rules"),
                       ("voice/Whisper + Gemma 4", "Voice, Whisper small + Gemma 4")):
        r = s[key]
        lines.append(f"{label:<34}{r['n']:>3}{r['hit1']:>8.2f}{r['p5']:>8.2f}{r['mrr']:>8.2f}{r['seconds']:>9.2f}")
    v = s["voice/Whisper + Gemma 4"]
    lines += [f"   Whisper: {v['utterances']} recordings, mean WER {v['wer']:.3f}, {v['transcribe_seconds']:.2f} s per "
              f"recording, order numbers kept {v['order_numbers_kept']}/{len(VOICE_ORDERS)}", "",
              "2. Image search (8 photos that differ from the shop images)",
              f"{'Reader':<34}{'n':>3}{'Hit@1':>8}{'Hit@3':>8}{'MRR':>8}{'s/query':>9}"]
    for mode in ("Gemma 4 vision", "local colour"):
        r = s[f"image/{mode}"]
        label = "Gemma 4 vision" if mode == "Gemma 4 vision" else "Local average colour (offline)"
        lines.append(f"{label:<34}{r['n']:>3}{r['hit1']:>8.2f}{r['hit3']:>8.2f}{r['mrr']:>8.2f}{r['seconds']:>9.2f}")
    lines += ["", "3. Assistant (orders and search)", f"{'Mode':<34}{'n':>3}{'correct':>9}{'tool ok':>9}{'leaks':>7}{'s':>7}"]
    for mode in ("Gemma 4 tools", "rules"):
        r = s[f"assistant/{mode}"]
        label = "Gemma 4 tool calling" if mode == "Gemma 4 tools" else "Rules (offline)"
        lines.append(f"{label:<34}{r['n']:>3}{r['correct']:>9}{r['tool_ok']:>9}{r['leaks']:>7}{r['seconds']:>7.2f}")
    lines += ["", "4. Room picks (Try it in your room, 3 sample rooms)",
              f"{'Mode':<34}{'picks':>6}{'reasons':>9}{'15-25 w':>9}{'concrete':>10}{'s/room':>8}"]
    for mode in ("Gemma 4", "vector fallback"):
        r = s[f"room/{mode}"]
        label = "Gemma 4 reads + picks" if mode == "Gemma 4" else "Vector ranking (offline)"
        lines.append(f"{label:<34}{r['picks']:>6}{r['reasons_present']:>9}{r['length_ok']:>9}{r['concrete']:>10}"
                     f"{r['seconds']:>8.2f}")
    lines += ["", "Details per query", ""]
    for r in text:
        lines.append(f"[text/{r['mode']}/{r['group']}] {r['request']!r}: top5 {r['top5']} relevant {r['relevant'][:6]}"
                     f" hit1={r['hit1']} p5={r['p5']} ({r['seconds']} s)")
    for r in voice:
        lines.append(f"[voice] {r['sample']} heard {r['transcript']!r} (ref {r['reference']!r}, WER {r['wer']})"
                     + (f" top5 {r['top5']} hit1={r['hit1']}" if "top5" in r else ""))
    for r in images:
        lines.append(f"[image/{r['mode']}] {r['query']} expected {r['expected']} rank {r['rank']} top3 {r['top3']}")
    for r in orders:
        lines.append(f"[assistant/{r['mode']}] {r['account']} {r['question']!r} -> {r['answer'][:150]!r}"
                     f" tools {r['tools']} correct={r['correct']} leaks={r['leaks']}")
    for r in rooms:
        for p in r["picks"]:
            lines.append(f"[room/{r['mode']}] {r['room']} {p['productId']}: {p['reason']} ({p['words']} words)")
    (OUT / "eval_summary.txt").write_text("\n".join(lines) + "\n")


def write_tex(s):
    t, k, v = s["text/Gemma 4/direct"], s["text/keyword rules/direct"], s["voice/Whisper + Gemma 4"]
    tp, kp = s["text/Gemma 4/paraphrased"], s["text/keyword rules/paraphrased"]
    gi, li = s["image/Gemma 4 vision"], s["image/local colour"]
    ga, ra = s["assistant/Gemma 4 tools"], s["assistant/rules"]
    gr, vr = s["room/Gemma 4"], s["room/vector fallback"]
    rows = [
        f"Text, Gemma 4 & {t['n']} & {t['hit1']:.2f} & {t['p5']:.2f} & {t['mrr']:.2f} & {t['seconds']:.2f} \\\\",
        f"Text, keyword rules (offline) & {k['n']} & {k['hit1']:.2f} & {k['p5']:.2f} & {k['mrr']:.2f} & {k['seconds']:.2f} \\\\",
        f"Paraphrased text, Gemma 4 & {tp['n']} & {tp['hit1']:.2f} & {tp['p5']:.2f} & {tp['mrr']:.2f} & {tp['seconds']:.2f} \\\\",
        f"Paraphrased text, keyword rules & {kp['n']} & {kp['hit1']:.2f} & {kp['p5']:.2f} & {kp['mrr']:.2f} & {kp['seconds']:.2f} \\\\",
        f"Voice, Whisper + Gemma 4 & {v['n']} & {v['hit1']:.2f} & {v['p5']:.2f} & {v['mrr']:.2f} & {v['seconds']:.2f} \\\\",
        f"Image, Gemma 4 vision & {gi['n']} & {gi['hit1']:.2f} & {gi['hit3']:.2f}$^*$ & {gi['mrr']:.2f} & {gi['seconds']:.2f} \\\\",
        f"Image, local colour (offline) & {li['n']} & {li['hit1']:.2f} & {li['hit3']:.2f}$^*$ & {li['mrr']:.2f} & {li['seconds']:.2f} \\\\",
    ]
    tex = ["% Generated by demo/scripts/evaluate.py — do not edit by hand.",
           "% evalSearchRows: input & n & Hit@1 & P@5 (image rows: Hit@3, starred) & MRR & seconds per query",
           "% evalAssistantRows: mode & n & correct & right tool & leaked words & seconds",
           "% evalRoomRows: mode & rooms & picks & reasons of 15-25 words & concrete reasons & seconds per room",
           "\\newcommand{\\evalSearchRows}{", *rows, "}",
           f"\\newcommand{{\\evalVoiceWer}}{{{v['wer']:.3f}}}",
           f"\\newcommand{{\\evalVoiceUtterances}}{{{v['utterances']}}}",
           "\\newcommand{\\evalAssistantRows}{",
           f"Gemma 4 tool calling & {ga['n']} & {ga['correct']} & {ga['tool_ok']} & {ga['leaks']} & {ga['seconds']:.2f} \\\\",
           f"Rules (offline) & {ra['n']} & {ra['correct']} & {ra['tool_ok']} & {ra['leaks']} & {ra['seconds']:.2f} \\\\", "}",
           "\\newcommand{\\evalRoomRows}{",
           f"Gemma 4 reads and picks & {gr['rooms']} & {gr['picks']} & {gr['length_ok']} & {gr['concrete']} & {gr['seconds']:.2f} \\\\",
           f"Vector ranking (offline) & {vr['rooms']} & {vr['picks']} & {vr['length_ok']} & {vr['concrete']} & {vr['seconds']:.2f} \\\\",
           "}"]
    (OUT / "eval_tables.tex").write_text("\n".join(tex) + "\n")


if __name__ == "__main__":
    main()
