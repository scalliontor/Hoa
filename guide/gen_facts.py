"""Writes build/guide/facts.tex for the Vietnamese presentation guide (guide/main.tex).

Every number and every slide title in the guide comes from the project itself, so the guide cannot drift from it:
  tools/model.py             requirement, use case, class, table counts
  build/code_stats5.tex      Java / JavaScript line counts and the number of tests
  build/test_results.txt     the code-versus-model check line
  build/eval/*.json          evaluation results (search, voice, assistant, room)
  slides/thuyettrinh_Hoa.pptx  slide titles
  guide/slides_vi.tex          the length of the Vietnamese script of each slide (for the timing)

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
WORDS_PER_MINUTE = 160  # Vietnamese syllable-words per minute at a calm presentation pace
SKIM_SECONDS = 8  # a slide that is only shown, not explained, in the short version
# Who says what (group 10): person 1 opens and does chapters 1-2, person 2 chapter 3, person 3 chapter 4,
# person 4 chapter 5, the demo and the conclusion. Slide 39 is the backup slide and belongs to nobody.
SPEAKERS = {"1": (1, 18), "2": (19, 26), "3": (27, 32), "4": (33, 38)}
CHAPTER_NAMES = {"1": "Requirement Determination", "2": "Analysis", "3": "AI in e-commerce", "4": "Design",
                 "5": "Code"}
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


def slide_text(slide):
    return " ".join(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)


def slide_data():
    """(number, title, seconds of speech, kind) per slide; kind is chapter N, conclusion, backup or ''."""
    prs = Presentation(str(ROOT / "slides" / "thuyettrinh_Hoa.pptx"))
    rows = []
    for number, slide in enumerate(prs.slides, 1):
        title = next((sh.text_frame.text.strip() for sh in slide.shapes
                      if sh.has_text_frame and sh.name == "Title"), None)
        text = slide_text(slide)
        kind = ""
        divider = re.search(r"CHAPTER 0(\d)", text)
        if title is None and divider:
            kind = f"chapter{divider.group(1)}"
            title = f"Chapter {divider.group(1)} - {CHAPTER_NAMES[divider.group(1)]}"
        elif title is None and number == 1:
            title = "Title slide"
        elif title is None and "Q&A" in text:
            title = "Questions & answers"
        if title is None:
            sys.exit(f"slide {number} has no title: teach slide_data() in guide/gen_facts.py about it")
        if "CONCLUSION" in text.upper().split("Họa.")[-1][:60] and title:
            kind = "conclusion"
        if "APPENDIX" in text and "BACKUP" in text:
            kind = "backup"
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        rows.append((number, title, len(notes.split()) * 60.0 / WORDS_PER_MINUTE, kind))
    return rows


def chapter_ranges(slides):
    """Chapter k runs from its divider to the slide before the next divider (or the conclusion)."""
    starts = {kind[-1]: n for n, _, _, kind in slides if kind.startswith("chapter")}
    conclusion = next(n for n, _, _, kind in slides if kind == "conclusion")
    backup = next(n for n, _, _, kind in slides if kind == "backup")
    ordered = sorted(starts.items(), key=lambda item: int(item[0]))
    ranges = []
    for i, (chapter, first) in enumerate(ordered):
        last = (int(ordered[i + 1][1]) if i + 1 < len(ordered) else conclusion) - 1
        ranges.append((chapter, first, last))
    ranges.append(("6", conclusion, backup - 1))
    ranges.append(("0", 1, int(ordered[0][1]) - 1))
    return ranges


def guide_slides():
    """Slide numbers that have text in guide/slides_vi.tex, the ones marked [must], and the deck titles it expects."""
    source = (ROOT / "guide" / "slides_vi.tex").read_text(encoding="utf-8")
    found = [(m.group(1) or "may", int(m.group(2))) for m in re.finditer(r"\\slide(?:\[(\w+)\])?\{(\d+)\}", source)]
    expected = {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"^% T(\d+): (.+)$", source, re.M)}
    return [n for _, n in found], {n for kind, n in found if kind == "must"}, expected


def read_group(src, i):
    """src[i] is '{'; returns (text inside the matching braces, index after them)."""
    depth, j = 0, i
    while j < len(src):
        if src[j] == "\\":
            j += 2
            continue
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces in guide/slides_vi.tex")


def parse_slides(source):
    """{number: dict(kind, idea, script, notes)} read from the \\slide blocks of guide/slides_vi.tex."""
    out = {}
    for m in re.finditer(r"\\slide(?:\[(\w+)\])?\{(\d+)\}", source):
        i, groups = m.end(), []
        for _ in range(3):
            while source[i] in " \n":
                i += 1
            group, i = read_group(source, i)
            groups.append(group)
        out[int(m.group(2))] = dict(kind=m.group(1) or "may", idea=groups[0], script=groups[1], notes=groups[2])
    return out


def drop_optional(script):
    """The script without the paragraphs marked \\luocbo{...} (they may be dropped when time is short)."""
    while True:
        k = script.find("\\luocbo{")
        if k < 0:
            return script
        _, end = read_group(script, k + len("\\luocbo"))
        script = script[:k] + script[end:]


def count_words(text):
    text = re.sub(r"\\cue\{[^{}]*\}", " ", text)             # stage directions are not spoken
    text = re.sub(r"\$[^$]*\$", " x ", text)                  # a formula is read as one word
    text = re.sub(r"\\(?:key|emph|textit|textbf|code|file|todo)\{", "{", text)
    text = re.sub(r"\\[a-zA-Z]+", " x ", text)                # \factXxx and other macros count as one word
    for ch in "{}~\\":
        text = text.replace(ch, " ")
    return len(text.split())


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
    wanted, must, expected = guide_slides()
    blocks = parse_slides((ROOT / "guide" / "slides_vi.tex").read_text(encoding="utf-8"))
    full = {n: count_words(b["script"]) * 60.0 / WORDS_PER_MINUTE for n, b in blocks.items()}
    core = {n: count_words(drop_optional(b["script"])) * 60.0 / WORDS_PER_MINUTE for n, b in blocks.items()}
    slides = [(n, t, full.get(n, 0.0), k) for n, t, _, k in slides]
    missing = [n for n, _, _, _ in slides if n not in wanted]
    extra = [n for n in wanted if n > len(slides)]
    if missing or extra or len(wanted) != len(set(wanted)):
        sys.exit(f"guide/slides_vi.tex does not match the deck: no text for slides {missing}, unknown slides {extra}, "
                 f"duplicates {sorted(n for n in set(wanted) if wanted.count(n) > 1)}")
    moved = [(n, expected[n], title) for n, title, _, _ in slides if n in expected and expected[n] != title]
    if moved:
        sys.exit("the deck changed under guide/slides_vi.tex (slide, title the guide expects, title in the deck): "
                 + "; ".join(map(str, moved)) + ". Renumber the guide, then update the '% T' comments.")
    unguarded = [n for n, _, _, _ in slides if n not in expected]
    if unguarded:
        sys.exit(f"slides {unguarded} have no '% T<number>: <title>' line in guide/slides_vi.tex")
    for number, title, seconds, _ in slides:
        out.append(f"\\expandafter\\def\\csname slideTitle{number}\\endcsname{{{tex(title)}}}")
        out.append(f"\\expandafter\\def\\csname slideTime{number}\\endcsname{{{minutes_text(seconds)}}}")
    macro("factSlides", len(slides))
    total = sum(s for _, _, s, _ in slides)
    short = sum(core[n] if n in must else SKIM_SECONDS for n, _, _, _ in slides)
    macro("timeFull", f"{total / 60:.0f}")
    macro("wpm", WORDS_PER_MINUTE)
    macro("scriptWords", sum(count_words(b["script"]) for b in blocks.values()))
    macro("timeShort", f"{short / 60:.0f}")
    macro("factMustSlides", len(must))
    for chapter, first, last in chapter_ranges(slides):
        seconds = sum(s for n, _, s, _ in slides if first <= n <= last)
        out.append(f"\\expandafter\\def\\csname chapterTime{chapter}\\endcsname{{{minutes_text(seconds)}}}")
        out.append(f"\\expandafter\\def\\csname chapterSlides{chapter}\\endcsname{{{first}--{last}}}")
    for person, (first, last) in SPEAKERS.items():
        in_range = [n for n, _, _, _ in slides if first <= n <= last]
        full_s = sum(full.get(n, 0.0) for n in in_range)
        short_s = sum(core[n] if n in must else SKIM_SECONDS for n in in_range)
        out.append(f"\\expandafter\\def\\csname speakerSlides{person}\\endcsname{{{first}--{last}}}")
        out.append(f"\\expandafter\\def\\csname speakerFull{person}\\endcsname{{{minutes_text(full_s)}}}")
        out.append(f"\\expandafter\\def\\csname speakerShort{person}\\endcsname{{{minutes_text(short_s)}}}")
    (OUT / "facts.tex").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"guide facts: {len(slides)} slides, ~{total / 60:.0f} min full, ~{short / 60:.0f} min short "
          f"({len(must)} must-say slides)")


if __name__ == "__main__":
    main()
