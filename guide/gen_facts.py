"""Writes build/guide/facts.tex for the Vietnamese defense guide (guide/main.tex).

Every number in the guide comes from the project itself, so the guide cannot drift from it:
  tools/model.py               requirement, use case, class, table and foreign-key counts
  build/test_results.txt       number of passing tests and the code-versus-model check line
  build/e2e_results.txt        end-to-end steps passed
  build/schema_comparison.txt  Visual Paradigm DDL compared with the running schema
  build/sql_validation.txt     constraint checks and sample rows of the generated database
  build/eval/*.json            evaluation results (search, voice, assistant, room)
  vp/diagrams.xml, figures/vp/README.md   diagrams of the VP project and the trial screenshots
  demo/src, demo/web/js        Java and JavaScript line counts
  guide/parts/03_kichban.tex   length of the spoken text of the 5-7 minute script (for the timing)

It stops with an error when a test or an end-to-end step failed, so the guide is never built on red evidence.

Usage (from tieuluan/): python3 guide/gen_facts.py      (guide/build.sh does it)
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import model  # noqa: E402

OUT = ROOT / "build" / "guide"
SCRIPT = ROOT / "guide" / "parts" / "03_kichban.tex"
WORDS_PER_MINUTE = 160  # Vietnamese syllable-words per minute at a calm presentation pace
SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$", "{": r"\{",
           "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def tex(text):
    return "".join(SPECIAL.get(ch, ch) for ch in str(text))


def pct(value, digits=0):
    return tex(f"{value * 100:.{digits}f}%")


def comma(value, digits):
    return tex(f"{value:.{digits}f}".replace(".", ","))


def need(pattern, text, source):
    found = re.search(pattern, text, re.M)
    if not found:
        sys.exit(f"{source}: no line matches {pattern!r}; update guide/gen_facts.py")
    return found.groups()


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
    raise ValueError(f"unbalanced braces in {SCRIPT}")


def spoken_parts(source):
    """The 'say' argument (the 4th of 7) of every \\buoc{...} block of the script."""
    said = []
    for m in re.finditer(r"\\buoc(?=\{)", source):
        i, groups = m.end(), []
        for _ in range(7):
            while source[i] in " \n%":
                i += 1
            group, i = read_group(source, i)
            groups.append(group)
        said.append(groups[3])
    return said


def count_words(text):
    text = re.sub(r"\\cue\{[^{}]*\}", " ", text)             # stage directions are not spoken
    text = re.sub(r"\\(?:key|emph|textit|textbf|code|file)\{", "{", text)
    text = re.sub(r"\\[a-zA-Z]+", " x ", text)                # \factXxx and other macros count as one word
    for ch in "{}~\\":
        text = text.replace(ch, " ")
    return len(text.split())


def line_count(folder, suffix):
    return sum(len(p.read_text(encoding="utf-8").splitlines()) for p in folder.rglob(f"*{suffix}"))


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
    macro("factDesignClasses", len(model.DESIGN))
    macro("factPackages", len({c["package"] for c in model.DESIGN}))
    macro("factTables", len(model.TABLES))
    macro("factFKs", len(list(model.foreign_keys())))
    macro("factLayers", len(model.LAYERS))

    # ---- tests and the model check (build/test_results.txt is written by demo/test.sh)
    results = (ROOT / "build" / "test_results.txt").read_text(encoding="utf-8")
    passed, failed = need(r"^(\d+) tests passed, (\d+) failed", results, "build/test_results.txt")
    if int(failed) or any(line.startswith("FAIL") for line in results.splitlines()):
        sys.exit("build/test_results.txt reports failing tests: fix them before building the guide")
    macro("factTests", passed)
    macro("factTestRun", tex(need(r"test run (\d{4}-\d\d-\d\d \d\d:\d\d)", results, "build/test_results.txt")[0]))
    check = need(r"Model check: (\d+) Java classes, (\d+) fields, (\d+) operations, (\d+) view functions, "
                 r"(\d+) tables, (\d+) columns, (\d+) SQL statements -> all match the model", results,
                 "build/test_results.txt")
    for name, value in zip(("factCheckClasses", "factCheckFields", "factCheckOps", "factCheckViews",
                            "factCheckTables", "factCheckColumns", "factCheckSql"), check):
        macro(name, value)

    # ---- end-to-end run, schema comparison, SQL validation
    e2e = (ROOT / "build" / "e2e_results.txt").read_text(encoding="utf-8")
    ok, total = need(r"^(\d+)/(\d+) steps passed", e2e, "build/e2e_results.txt")
    if ok != total:
        sys.exit(f"build/e2e_results.txt: only {ok}/{total} steps passed")
    macro("factEtoE", ok)
    compare = (ROOT / "build" / "schema_comparison.txt").read_text(encoding="utf-8")
    same, _, cols = need(r"primary keys and UNIQUE: (\w+) \((\d+) tables, (\d+) columns compared\)",
                         compare, "build/schema_comparison.txt")
    if same != "True":
        sys.exit("build/schema_comparison.txt: the VP DDL and the schema differ")
    macro("factCmpColumns", cols)
    vp_fk, vp_check = need(r"writes no FOREIGN KEY \((\d+) in the schema\) and no CHECK \((\d+) in the schema\)",
                           compare, "build/schema_comparison.txt")
    macro("factSchemaFKs", vp_fk)
    macro("factSchemaChecks", vp_check)
    sql = (ROOT / "build" / "sql_validation.txt").read_text(encoding="utf-8")
    macro("factSampleRows", need(r"(\d+) sample rows", sql, "build/sql_validation.txt")[0])
    rejected, broken = need(r"^(\d+)/(\d+) statements that break a constraint were rejected", sql,
                            "build/sql_validation.txt")
    macro("factSqlRejected", f"{rejected}/{broken}")
    macro("factMisplaced", need(r"not in the table of their category: (\d+)", sql, "build/sql_validation.txt")[0])

    # ---- diagrams of the Visual Paradigm project
    diagrams = (ROOT / "vp" / "diagrams.xml").read_text(encoding="utf-8")
    macro("factDiagrams", len(re.findall(r"<diagram ", diagrams)))
    trial = len(re.findall(r"\*Trial screenshot\.\*", (ROOT / "figures" / "vp" / "README.md").read_text("utf-8")))
    macro("factTrial", trial)

    # ---- code and catalogue
    macro("factJavaLines", line_count(ROOT / "demo" / "src" / "main" / "java", ".java"))
    macro("factJsLines", line_count(ROOT / "demo" / "web" / "js", ".js"))
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
    macro("evTextSecGemma", comma(ev["text/Gemma 4/direct"]["seconds"], 2))
    macro("evTextSecRules", comma(ev["text/keyword rules/direct"]["seconds"], 3))
    macro("evVoiceHit", pct(ev["voice/Whisper + Gemma 4"]["hit1"]))
    macro("evVoiceN", ev["voice/Whisper + Gemma 4"]["n"])
    macro("evVoiceWer", pct(ev["voice/Whisper + Gemma 4"]["wer"], 1))
    macro("evImageGemma", pct(ev["image/Gemma 4 vision"]["hit1"]))
    macro("evImageLocal", pct(ev["image/local colour"]["hit1"]))
    macro("evImageN", ev["image/Gemma 4 vision"]["n"])
    macro("evAssistantCorrect", ev["assistant/Gemma 4 tools"]["correct"])
    macro("evAssistantN", ev["assistant/Gemma 4 tools"]["n"])
    macro("evAssistantLeaks", ev["assistant/Gemma 4 tools"]["leaks"])
    room = ev["room/Gemma 4"]
    macro("evRoomPicks", room["picks"])
    macro("evRoomConcrete", room["concrete"])
    voice = json.loads((ROOT / "build" / "eval" / "voice_eval.json").read_text(encoding="utf-8"))["en"]["summary"]
    macro("evSttWer", pct(voice["wer"], 1))
    macro("evSttMean", comma(voice["mean_seconds"], 2))
    macro("evSttMax", comma(voice["max_seconds"], 2))
    macro("evSttN", voice["n_utterances"])

    # ---- the spoken part of the 5-7 minute script
    said = spoken_parts(SCRIPT.read_text(encoding="utf-8"))
    if len(said) != 7:
        sys.exit(f"{SCRIPT.name}: expected 7 \\buoc blocks (the seven steps of the script), found {len(said)}")
    words = sum(count_words(text) for text in said)
    macro("wpm", WORDS_PER_MINUTE)
    macro("scriptWords", words)
    macro("timeSpeech", comma(words / WORDS_PER_MINUTE, 1))
    (OUT / "facts.tex").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"guide facts: {passed} tests, e2e {ok}/{total}, script {words} words "
          f"(~{words / WORDS_PER_MINUTE:.1f} min of speech)")


if __name__ == "__main__":
    main()
