"""Writes the Chapter 5 build outputs from the real code:
../build/excerpts5/<name>.java|.js (chosen methods, at most 45 lines), ../build/code_tree5.txt and
../build/code_stats5.tex (\\javaFileCount, \\javaLineCount, \\jsFileCount, \\testCount).

Usage (from demo/): python3 scripts/make_excerpts.py
"""
import re
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1]
BUILD = DEMO.parent / "build"
JAVA = DEMO / "src" / "main" / "java" / "com" / "ptit" / "ecom"
MAX_LINES = 45

# excerpt name -> (source file, methods to show in this order)
EXCERPTS = {
    "EcomApplication.java": ("presentation/web/EcomApplication.java", ["main"]),
    "WebServer_routes.java": ("presentation/web/WebServer.java", ["route", "customer"]),
    "SearchService.java": ("application/search/SearchService.java", ["searchRoom", "retrieve"]),
    "QueryService.java": ("application/search/QueryService.java", ["textQuery", "understand"]),
    "ImageService.java": ("application/search/ImageService.java", ["embed", "describe", "askGemma"]),
    "VectorIndex.java": ("infrastructure/search/VectorIndex.java", ["toVector", "cosineSimilarity", "nearest"]),
    "RankingService.java": ("application/search/RankingService.java", ["rank", "businessScore"]),
    "GemmaClient.java": ("infrastructure/ai/GemmaClient.java", ["chat"]),
    "WhisperClient.java": ("infrastructure/ai/WhisperClient.java", ["transcribe", "isAvailable"]),
    "AssistantService.java": ("application/service/AssistantService.java", ["ask", "tools"]),
    "CheckoutService.java": ("application/service/CheckoutService.java", ["checkout", "currentProduct"]),
    "OrderService.java": ("application/service/OrderService.java", ["getOrder", "cancelOrder", "updateStatus"]),
    "SqliteOrderRepository.java": ("infrastructure/repository/sqlite/SqliteOrderRepository.java",
                                   ["findOrder", "save"]),
    "search_ui.js": ("web/js/search-ui.js", ["submitText", "submitVoice", "submitImage", "submitMultimodal"]),
    "voice_input.js": ("web/js/voice-input.js", ["start", "upload"]),
}


def method_lines(lines, name, javascript):
    """The lines of one method or function, with its Javadoc and annotations, by brace matching."""
    if javascript:
        pattern = re.compile(rf"^\s*(async\s+)?(function\s+)?{name}\s*(=\s*(async\s*)?)?(\(|:\s*(async\s*)?\()")
    else:
        pattern = re.compile(rf"^\s+(public|private|protected|static)[^=;]*?\b{name}\s*\(")
    start = next((i for i, line in enumerate(lines) if pattern.search(line)), None)
    if start is None:
        return []
    first = start
    while first > 0 and (lines[first - 1].strip().startswith(("@", "*", "/**", "//"))):
        first -= 1
    depth, end, opened = 0, start, False
    for end in range(start, len(lines)):
        code = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`|//.*', "", lines[end])
        depth += code.count("{") - code.count("}")
        opened = opened or "{" in code
        if opened and depth <= 0:
            break
    return lines[first:end + 1]


def excerpt(name, source, methods):
    path = DEMO / source if source.startswith("web/") else JAVA / source
    if not path.exists():
        return None
    lines = path.read_text().splitlines()
    javascript = path.suffix == ".js"
    head = [] if javascript else [next(line for line in lines if re.match(r"public (abstract )?(class|interface)", line))]
    body = []
    for method in methods:
        found = method_lines(lines, method, javascript)
        if found:
            body += ([("  " if javascript else "    ") + "// ..."] if body or head else []) + found
    text = head + body + ([] if javascript else ["    // ...", "}"])
    return text


def tree():
    skip_dirs = {"build", ".venv", "__pycache__", "classes", "test-classes", ".tools"}
    summaries = {"web/img": "painting images P01-P32, rooms/ (3 sample rooms + rooms.json), credits.json",
                 "web/fonts": "web fonts", "data/eval_images": "8 photos used as image queries in the evaluation",
                 "generated/src": "58 generated classes, same packages as src/main/java",
                 "voice-server/samples": "recorded test requests (en, vi)"}
    out = ["demo/"]

    def walk(folder, prefix):
        entries = sorted(p for p in folder.iterdir() if p.name not in skip_dirs and not p.name.startswith("."))
        entries = [p for p in entries if not p.name.endswith((".log", ".db"))]
        for i, entry in enumerate(entries):
            last = i == len(entries) - 1
            relative = entry.relative_to(DEMO).as_posix()
            out.append(f"{prefix}{'└── ' if last else '├── '}{entry.name}{'/' if entry.is_dir() else ''}"
                       + (f"   ({summaries[relative]})" if relative in summaries else ""))
            if entry.is_dir() and relative not in summaries:
                walk(entry, prefix + ("    " if last else "│   "))

    walk(DEMO, "")
    return "\n".join(out) + "\n"


def main():
    folder = BUILD / "excerpts5"
    folder.mkdir(parents=True, exist_ok=True)
    for name, (source, methods) in EXCERPTS.items():
        lines = excerpt(name, source, methods)
        if lines is None:
            print(f"skip {name}: {source} not found")
            continue
        if len(lines) > MAX_LINES:
            print(f"warning: {name} has {len(lines)} lines (limit {MAX_LINES})")
        (folder / name).write_text("\n".join(lines) + "\n")
        print(f"{name}: {len(lines)} lines")
    (BUILD / "code_tree5.txt").write_text(tree())
    java_files = sorted(JAVA.rglob("*.java"))
    js_files = sorted((DEMO / "web" / "js").glob("*.js"))
    test_text = " ".join(p.read_text() for p in (DEMO / "tests" / "java").rglob("*.java"))
    stats = {"javaFileCount": len(java_files),
             "javaLineCount": sum(len(p.read_text().splitlines()) for p in java_files),
             "jsFileCount": len(js_files),
             "jsLineCount": sum(len(p.read_text().splitlines()) for p in js_files),
             "testCount": len(re.findall(r'\btest\("', test_text))}
    (BUILD / "code_stats5.tex").write_text("% Written by demo/scripts/make_excerpts.py\n" + "".join(
        f"\\providecommand{{\\{k}}}{{{v}}}\n" for k, v in stats.items()))
    print(stats)


if __name__ == "__main__":
    main()
