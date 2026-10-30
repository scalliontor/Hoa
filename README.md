# Họa. — essay, demo and slides (PTIT ISAD, class 04)

Painting shop "Họa." (public-domain prints and frames) used as the running example of the five chapters:
Requirement Determination, Analysis, AI in E-commerce, Design, Code.

## Where to find things

| What | Path |
|---|---|
| Essay (PDF) | `build/report/tieuluan_V2_04_<group>_<NAME>.pdf` (rebuild: `report/build.sh`) |
| Essay (LaTeX source) | `report/main.tex`, `report/chapters/ch1_requirements.tex` … `ch5_code.tex` |
| Presentation | `slides/thuyettrinh_Hoa.pptx` (rebuild: `slides/.venv/bin/python slides/build_slides.py`) |
| Demo (run it) | `demo/run.sh` → http://127.0.0.1:8686 |
| Single source of truth | `tools/model.py`: requirements, use cases, classes, methods, layers, tables |
| Visual Paradigm project | `vp/tieuluan_design.vpp` (built by `tools/build_vp.py` + `vp/plugin/`) |
| Diagrams (PNG/SVG) | `figures/vp/<id>.png`, see `figures/vp/README.md` |
| Demo screenshots | `figures/demo/<name>.png` |
| Test, evaluation, excerpts | `build/test_results.txt`, `build/eval/`, `build/excerpts5/` |
| Old Chapter 4 (submitted 28/10) | `_archive/chapter4_submitted_2026-10-28/` |

## Reading the essay next to the files

| Section | Look at |
|---|---|
| 1 Requirements (FR/NFR, use cases, MoSCoW) | `tools/model.py` (`REQUIREMENTS`, `USE_CASES`), `figures/vp/c1_*.png` |
| 2 Analysis (use case specs, activity, domain, sequence, state) | `figures/vp/c2_*.png`, `tools/model.py` (`ANALYSIS`) |
| 3 AI in e-commerce (Gemma 4, Whisper, image, room, assistant) | `demo/src/main/java/com/ptit/ecom/application/search/`, `…/infrastructure/ai/`, `demo/voice-server/`, `build/eval/` |
| 4.1 Class diagram in analysis | `figures/vp/c41_analysis.png` |
| 4.2 Data model – database | `figures/vp/c42_*.png`, `demo/db/ecom_schema_sqlite.sql`, `demo/db/seed.sql`, `tools/gen_sql.py` |
| 4.3 Class diagram in design | `figures/vp/c43_design.png`, `tools/model.py` (`DESIGN`) |
| 4.4 Layers + classes + relations | `figures/vp/c44_*.png`, `tools/model.py` (`LAYERS`) |
| 4.5 Generated code | `tools/gen_java.py` → `demo/generated/src/`, check: `tools/check_code_model.py` |
| 5 Code (stack, deployment, UI, tests) | `demo/src/main/java/`, `demo/web/`, `demo/tests/java/`, `demo/API.md` |

## Demo layout

```
demo/
├── run.sh, build.sh, test.sh   start / compile / test (JDK 17+, e.g. brew install openjdk@21)
├── config/app.properties       port 8686, Gemma 4 endpoint, Whisper, ranking weights α β γ
├── src/main/java/com/ptit/ecom/
│   ├── presentation/  view (JS views live in web/js), controller, web (WebServer, SessionManager)
│   ├── application/   service (Cart, Checkout, Order, Product, Assistant), search (Query, Search, Ranking…)
│   ├── domain/        customer, product, cart, order, payment
│   └── infrastructure/ repository (+ sqlite), search (VectorIndex), ai (GemmaClient, WhisperClient)
├── web/            HTML, CSS, one JS file per view class (web/README.md maps files to classes)
├── voice-server/   self-hosted Whisper (faster-whisper "small") on 127.0.0.1:9000
├── db/ data/       SQLite schema + seed, painting catalogue, image credits, evaluation photos
└── tests/java/     plain Java test runner with fake AI clients
```

Demo accounts: C001 Nguyen Minh An (VIP), C002 Tran Thu Binh (new customer), ADMIN (gallery staff).
Gemma 4 runs on the remote L40S server; when it is unreachable, search falls back to keyword and vector matching.
