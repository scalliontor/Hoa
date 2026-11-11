# showcase: defense page of the essay

`showcase/index.html` is a single static page used at the oral defense of the individual essay
"Information System Analysis and Design: Họa." (PTIT, class 04). From any requirement, the reader can click
through to its use case, the essay section (PDF page), the Visual Paradigm diagrams, the design signature in
`tools/model.py`, the exact lines of code on GitHub, the HTTP route, the browser view, the database tables
and the tests.

GitHub Pages serves the repository root, so the page is at `https://scalliontor.github.io/Hoa/showcase/`.
The page is static. The shop itself is not hosted there: it runs on the presenter's laptop with `demo/run.sh`.

## Sections

| | Section | Content |
|---|---|---|
| | Hero | title, author, buttons (essay PDF, VP project, GitHub, run locally), key numbers |
| A | Project overview | problems P1–P5, goals, users, functional scope, highlights |
| B | Development process | requirements → analysis → design → implementation → verification, with UC07 followed through all five |
| C | Diagram evolution | classes, data and behaviour chains, with what changed, why and the benefit at every step, ending in real code |
| D | Design-to-code traceability | UC02, UC04, UC07, UC11, UC13: requirement, analysis, design, implementation (route, view, methods, tables), tests |
| E | Database design & generation | table groups, the category/product/detail tables, mapping rules, model ↔ schema comparison, VP evidence |
| F | Live demo | how to start the shop, demo accounts, five scripted flows with screenshots |
| G | Verification & conclusion | requirements matrix, test and check results, AI evaluation, limitations, design decisions |
| + | All diagrams | every VP figure in essay order, by chapter; click a card for the lightbox (←/→, Esc) |

## Rebuild

```bash
python3 tools/build_showcase.py
```

Python 3.9+ and the standard library only. The output is deterministic. Rebuild after any change to the model,
the essay, the figures, the demo code or the test and evaluation results. Nothing on the page is typed by hand:

- counts, requirements, use cases, classes, signatures, tables and foreign keys come from `tools/model.py`;
- figure descriptions come from `figures/vp/README.md`; figure order, numbers and captions come from
  `report/chapters/*.tex`; page numbers come from the named destinations of the essay PDF;
- test results come from `build/test_results.txt`, the AI evaluation from `build/eval/`, the SQL check from
  `build/sql_validation.txt`; `tools/check_code_model.py` is run during the build;
- code links (`blob/main/<path>#L<line>`) are found by searching the sources for the class, method, route,
  view function or test, so they follow the code when it moves;
- the tables a use case reaches are found by following the calls from its controller method to the SQL of the
  SQLite repositories; the schema and seed are loaded into an in-memory SQLite database and compared with the model.

The generator stops with an error if a referenced file, figure, class, method, test, route or table is missing.
It then checks every link of the written page (anchors, repository files, GitHub line ranges) and compares the
linked lines with `origin/main`. Warnings list what GitHub does not have yet (files not pushed, lines that moved),
an essay PDF older than its LaTeX sources, and VP figures that do not yet show every table of the model.

## Look

The page follows the shop's own design (`demo/web/css`): dark by default with a light switch, Inter Tight and
JetBrains Mono from `demo/web/fonts`, monospaced upper-case labels, images on a "wall", the Họa. word mark.
All CSS and JS are inline; images and fonts are referenced relatively from the repository.

To view it locally: `python3 -m http.server` in the repository root, then open `http://localhost:8000/showcase/`.
