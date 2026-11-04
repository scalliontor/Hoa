"""Writes build/guide/facts.tex for the Vietnamese presentation guide (guide/main.tex).

Every number and every slide title in the guide comes from the project itself, so the guide cannot drift from it:
  tools/model.py             requirement, use case, class, table counts
  build/code_stats5.tex      Java / JavaScript line counts and the number of tests
  build/test_results.txt     the code-versus-model check line
  build/eval/*.json          evaluation results (search, voice, assistant, room)
  slides/thuyettrinh_Hoa.pptx  slide titles and the length of the speaker notes (for the timing)

It also stops with an error when a slide has no text in guide/slides_vi.tex (or the other way round), so the guide
is rebuilt whenever the deck changes.

Usage (from tieuluan/): slides/.venv/bin/python guide/gen_facts.py      (guide/build.sh does it)
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402
from pptx import Presentation  # noqa: E402

OUT = ROOT / "build" / "guide"
WORDS_PER_MINUTE = 130  # speaking speed used to turn the length of the speaker notes into a time estimate
# Slides without a shape named "Title" (the title slide, the chapter dividers, the Q&A slide).
FIXED_TITLES = {1: "Title slide", 4: "Chapter 1 - Requirement Determination", 10: "Chapter 2 - Analysis",
                15: "Chapter 3 - AI in e-commerce", 23: "Chapter 4 - Design", 28: "Chapter 5 - Code",
                33: "Questions & answers"}
CHAPTERS = [("1", 4, 9), ("2", 10, 14), ("3", 15, 22), ("4", 23, 27), ("5", 28, 31), ("6", 32, 33)]  # first, last slide
SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$", "{": r"\{",
           "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\u2194": " <-> ",
           "\u2260": " != ", "\u25aa": "-", "\u2192": "->", "\u2014": "-", "\u2013": "-"}


def tex(text):
    return "".join(SPECIAL.get(ch, ch) for ch in text)


def pct(value, digits=0):
    return tex(f"{value * 100:.{digits}f}%")


def minutes_text(seconds):
    seconds = max(5, int(round(seconds / 5.0)) * 5)
    if seconds < 60:
        return f"{seconds} giây"
    minutes, rest = divmod(seconds, 60)
    return f"{minutes} phút" + (f" {rest} giây" if rest else "")


def slide_data():
    prs = Presentation(str(ROOT / "slides" / "thuyettrinh_Hoa.pptx"))
    rows = []
    for number, slide in enumerate(prs.slides, 1):
        title = next((sh.text_frame.text.strip() for sh in slide.shapes
                      if sh.has_text_frame and sh.name == "Title"), FIXED_TITLES.get(number))
        if not title:
            sys.exit(f"slide {number} has no title: add it to FIXED_TITLES in guide/gen_facts.py")
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        rows.append((number, title, len(notes.split()) * 60.0 / WORDS_PER_MINUTE))
    return rows


def guide_slides():
    """Slide numbers that have text in guide/slides_vi.tex, and the ones marked [must]."""
    source = (ROOT / "guide" / "slides_vi.tex").read_text(encoding="utf-8")
    found = [(m.group(1) or "may", int(m.group(2))) for m in re.finditer(r"\\slide(?:\[(\w+)\])?\{(\d+)\}", source)]
    return [n for _, n in found], {n for kind, n in found if kind == "must"}


def read_macros(path):
    return {m.group(1): m.group(2) for m in re.finditer(r"\\providecommand\{\\(\w+)\}\{(\d+)\}",
                                                        path.read_text(encoding="utf-8"))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    out = []

    def macro(name, value):
        out.append(f"\\newcommand{{\\{name}}}{{{value}}}")

    # ---- the specification
    fr = [r for r in model.REQUIREMENTS if r[1] == "FR"]
    nfr = [r for r in model.REQUIREMENTS if r[1] == "NFR"]
    moscow = {k: sum(1 for r in fr if model.REQUIREMENT_DETAILS[r[0]][0] == k) for k in ("Must", "Should", "Could")}
    macro("factReq", len(model.REQUIREMENTS))
    macro("factFR", len(fr))
    macro("factNFR", len(nfr))
    macro("factMust", moscow["Must"])
    macro("factShould", moscow["Should"])
    macro("factCould", moscow["Could"])
    macro("factUC", len(model.USE_CASES))
    macro("factActors", len(model.ACTORS))
    macro("factAnalysis", len(model.ANALYSIS))
    views = sum(1 for c in model.DESIGN if c.get("kind") == "view")
    macro("factJavaClasses", len(model.DESIGN) - views)
    macro("factJsViews", views)
    macro("factPackages", len({c["package"] for c in model.DESIGN}))
    macro("factTables", len(model.TABLES))
    macro("factFKs", len(model.FK_LABELS))
    macro("factLayers", len(model.LAYERS))

    # ---- code statistics and the model check
    stats = read_macros(ROOT / "build" / "code_stats5.tex")
    macro("factTests", stats["testCount"])
    macro("factJavaLines", stats["javaLineCount"])
    macro("factJsLines", stats["jsLineCount"])
    results = (ROOT / "build" / "test_results.txt").read_text(encoding="utf-8")
    failed = sum(1 for line in results.splitlines() if line.startswith("FAIL"))
    if failed:
        sys.exit(f"build/test_results.txt reports {failed} failing tests: fix them before building the guide")
    check = re.search(r"Model check: (\d+) Java classes, (\d+) fields, (\d+) operations, (\d+) view functions, "
                      r"(\d+) tables, (\d+) columns", results)
    for name, value in zip(("factCheckClasses", "factCheckFields", "factCheckOps", "factCheckViews",
                            "factCheckTables", "factCheckColumns"), check.groups() if check else ["?"] * 6):
        macro(name, value)

    # ---- catalogue
    catalog = json.loads((ROOT / "demo" / "data" / "catalog.json").read_text(encoding="utf-8"))
    macro("factPaintings", len(catalog["paintings"]))
    macro("factFrames", len(catalog["frames"]))

    # ---- evaluation
    ev = json.loads((ROOT / "build" / "eval" / "eval_results.json").read_text(encoding="utf-8"))["summary"]
    macro("evTextDirectGemma", pct(ev["text/Gemma 4/direct"]["hit1"]))
    macro("evTextDirectRules", pct(ev["text/keyword rules/direct"]["hit1"]))
    macro("evTextDirectN", ev["text/Gemma 4/direct"]["n"])
    macro("evTextParaGemma", pct(ev["text/Gemma 4/paraphrased"]["hit1"]))
    macro("evTextParaRules", pct(ev["text/keyword rules/paraphrased"]["hit1"]))
    macro("evTextParaN", ev["text/Gemma 4/paraphrased"]["n"])
    macro("evTextSecGemma", tex(f"{ev['text/Gemma 4/direct']['seconds']:.2f}".replace(".", ",")))
    macro("evTextSecRules", tex(f"{ev['text/keyword rules/direct']['seconds']:.3f}".replace(".", ",")))
    macro("evVoiceHit", pct(ev["voice/Whisper + Gemma 4"]["hit1"]))
    macro("evVoiceN", ev["voice/Whisper + Gemma 4"]["n"])
    macro("evVoiceWer", pct(ev["voice/Whisper + Gemma 4"]["wer"], 1))
    macro("evVoiceUtterances", ev["voice/Whisper + Gemma 4"]["utterances"])
    macro("evImageGemma", pct(ev["image/Gemma 4 vision"]["hit1"]))
    macro("evImageGemmaThree", pct(ev["image/Gemma 4 vision"]["hit3"]))
    macro("evImageLocal", pct(ev["image/local colour"]["hit1"]))
    macro("evImageLocalThree", pct(ev["image/local colour"]["hit3"]))
    macro("evImageN", ev["image/Gemma 4 vision"]["n"])
    macro("evAssistantCorrect", ev["assistant/Gemma 4 tools"]["correct"])
    macro("evAssistantN", ev["assistant/Gemma 4 tools"]["n"])
    macro("evAssistantLeaks", ev["assistant/Gemma 4 tools"]["leaks"])
    room = ev["room/Gemma 4"]
    macro("evRoomPicks", room["picks"])
    macro("evRoomConcrete", room["concrete"])
    voice = json.loads((ROOT / "build" / "eval" / "voice_eval.json").read_text(encoding="utf-8"))["en"]["summary"]
    macro("evSttWer", pct(voice["wer"], 1))
    macro("evSttMean", tex(f"{voice['mean_seconds']:.2f}".replace(".", ",")))
    macro("evSttMax", tex(f"{voice['max_seconds']:.2f}".replace(".", ",")))
    macro("evSttExact", voice["exact_sentences"])
    macro("evSttN", voice["n_utterances"])

    # ---- slides: titles, estimated time, check against slides_vi.tex
    slides = slide_data()
    wanted, must = guide_slides()
    missing = [n for n, _, _ in slides if n not in wanted]
    extra = [n for n in wanted if n > len(slides)]
    if missing or extra or len(wanted) != len(set(wanted)):
        sys.exit(f"guide/slides_vi.tex does not match the deck: no text for slides {missing}, unknown slides {extra}, "
                 f"duplicates {sorted(n for n in set(wanted) if wanted.count(n) > 1)}")
    for number, title, seconds in slides:
        out.append(f"\\expandafter\\def\\csname slideTitle{number}\\endcsname{{{tex(title)}}}")
        out.append(f"\\expandafter\\def\\csname slideTime{number}\\endcsname{{{minutes_text(seconds)}}}")
    macro("factSlides", len(slides))
    total = sum(s for _, _, s in slides)
    short = sum(s for n, _, s in slides if n in must)
    macro("timeFull", f"{total / 60:.0f}")
    macro("timeShort", f"{short / 60:.0f}")
    macro("factMustSlides", len(must))
    for chapter, first, last in CHAPTERS:
        seconds = sum(s for n, _, s in slides if first <= n <= last)
        out.append(f"\\expandafter\\def\\csname chapterTime{chapter}\\endcsname{{{minutes_text(seconds)}}}")
        out.append(f"\\expandafter\\def\\csname chapterSlides{chapter}\\endcsname{{{first}--{last}}}")
    (OUT / "facts.tex").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"guide facts: {len(slides)} slides, ~{total / 60:.0f} min full, ~{short / 60:.0f} min short "
          f"({len(must)} must-say slides)")


if __name__ == "__main__":
    main()
