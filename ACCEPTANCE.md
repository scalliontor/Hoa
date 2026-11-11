# Họa. — requirement matrix, diagram inventory, plan and acceptance

Defense: **Thursday 12/11/2026, 18:00 (GMT+7)**. Individual essay of Vũ Hùng Anh (B23DCDT022), class 04.
This file is the single control sheet: it is updated while the work goes on and ends as the acceptance checklist.
Status: PASS (verified, evidence named) / PARTIAL / BLOCKED / NOT STARTED.

## Sources of the requirements

The course context is `PT&TKHTTT/` (the folder the guideline calls `07 tieuluan`).

| Source | What it fixes |
|---|---|
| Board photos `PT&TKHTTT/Theory & Requirement/*.png, *.jpg` | Five chapters of about 15 pages; Chapter 4 outline 4.1-4.6 (analysis classes, data model and database with "generate DB", design classes, layers + classes + relationships, code generated from 4.4, conclusion); checklist Analysis (class, activity, context) / Data model (class diagram with labels, multiplicities, ORM; data model; database) / Design (classes with methods, layers + relationships, database revised) / Code (code matches design, uses the DB); final evaluation and demo 12/11 and 19/11 |
| Slides 01-05, slide 03 class model, assignments 01, 02, 03, 06 (same folder) | Notation and content of each phase |
| `TỪ PHÂN TÍCH ĐẾN THIẾT KẾ.pdf` (lecturer's appendix) | Analysis to design in four steps: methods on classes, association to «use», DAO (interface + implementation), three layers MVC with packages; the lecturer's own figures are screenshots of Visual Paradigm Enterprise (Evaluation Copy) |
| `Integrating_AI_E-Commerce-Analysis_phase.pdf` | AI in the analysis phase (Chapter 3) |
| `Reference/tieuluan_V4_03_01_NhiCT.075.pdf` | Structure of a finished essay (structure only, no wording) |
| Lecturer's feedback on products (user guideline 6.2) | Classify products by `Category`; common data in `Product`; specific data in detail tables |
| User guideline of 11/11/2026 | Diagram list per phase, native VP project, database generated from the physical model, code that follows the design, traceability, tests, defense showcase, defense guide |

## Requirement and deliverable matrix

| # | Item | Requirement | Source | Phase | Deliverable | Acceptance criterion | Status |
|---|---|---|---|---|---|---|---|
| R1 | Essay | Five chapters, individual | Board | all | `build/report/tieuluan_V3_04_10_VUHUNGANH_022.pdf` | Builds with 0 overfull boxes, 0 undefined references | PASS (report/build.sh 11/11 23:11: 191 pages, 0 overfull, 0 undefined references; every generated table row explained) |
| R2 | Business understanding | Context, stakeholder map, business process, problem tree | Guideline 4.1, slide 01 | Requirements | c1_dfd0, c1_stakeholders, c1_process, c1_problems | In VP project, in Ch. 1, explained | PASS |
| R3 | Use cases | Overview and detail per area, specifications with alternative flows | Slides 02-03 | Requirements | c1_usecase, c2_uc_*, spec tables | Every UC of the overview in a detail diagram; 7 specified UCs with >= 3 alternatives | PASS |
| R4 | Behaviour analysis | DFD, activity, analysis sequence | Guideline 4.1, slide 03 | Analysis | c2_dfd1, 6 activities, 3 BCE sequences | Analysis objects only (no code classes) | PASS |
| R5 | Analysis classes | Domain model with attributes and relationship kinds | Slide 04, A03 | Analysis | c2_domain | Not a copy of the tables | PASS (Category added; c2_domain/c41_analysis rebuilt 11/11 23:05, inspected) |
| R6 | Data model | Conceptual -> logical -> physical -> database | Guideline 6 | Analysis/Design | c42_conceptual, c42_orm, c42_tables, c42_erd | Names and cardinalities agree across levels | PASS (conceptual, logical, physical, ERD rebuilt with category; names and multiplicities from one model) |
| R7 | Category / Product / detail | Category table, common Product, detail tables | Lecturer feedback | Design | model.py TABLES, schema, code | FK product.category_id; category says which detail table; tests | PASS (model.py Category/DetailKind/category table; schema+seed: 2 categories, 37 products, 0 detail rows in the wrong table (build/sql_validation.txt); code: SqliteProductRepository picks the detail table by detailKind, save refused when Category.accepts fails; tests 67/67) |
| R8 | DB generated in VP | Generate database / DDL from the physical model, screenshots, comparison | Guideline 6.3 | Design | DDL + screenshots + comparison script | Generated DDL matches the running schema except documented differences | PARTIAL. Done: VP's own SQL generator (DatabaseManager.generateCreateSQL, SQLite dialect, project database configuration saved in the .vpp) wrote demo/db/vp_generated_ddl.sql from the 18 ERD tables; build/schema_comparison.txt: same tables, columns, types, NOT NULL, PK, UNIQUE (FK and CHECK not written by VP's SQLite dialect, added by gen_sql.py from the same model). Missing: a screenshot of the Generate Database wizard, because VP's ribbon cannot be driven from a plugin. Manual steps for a live show: open vp/tieuluan_design.vpp in the trial edition, open '4.2 Database - entity relationship diagram', Tools > DB > Generate Database, keep SQLite (already configured), choose 'Generate DDL' to a file, then run python3 tools/compare_schema.py |
| R9 | Design | Three logical components, design classes, design sequences | Guideline 4.1, slide 05 | Design | component diagram, c43_design, c44_*, 3 design sequences | Every operation in a sequence exists in model and code | PASS (c44_components added; 3 design sequences; operations asserted against model.DESIGN) |
| R10 | Code follows design | Names, signatures, tables, SQL match the model | Guideline 7 | Implementation | `tools/check_code_model.py` | "all match the model" | PASS (demo/test.sh 11/11 23:05: 60 Java classes, 18 tables, 91 columns, 62 SQL -> all match the model) |
| R11 | Tests | Behaviour tests, e2e of the main flows | Guideline 10 | Verification | `demo/test.sh`, e2e run | All pass; evidence saved | PASS (67/67 unit and integration tests; tools/e2e_check.py 17/17 with Gemma online and offline, build/e2e_results.txt 11/11) |
| R12 | Demo | Main flows complete, good UI, error states | Guideline 8 | Implementation | `demo/` on :8686 | Scripted walk-through without failure | PASS (screenshots of the painting detail page and the back office retaken 11/11 23:47 with the category; all flows end to end with Gemma 4 at DeepInfra: text, image P10 first, assistant with tools, ownership; fallbacks with Gemma unreachable) |
| R13 | Traceability | Requirement -> UC -> analysis -> design -> code (line) -> table -> test | Guideline 9 | all | showcase section D, essay tables | Links open real artefacts | PASS (showcase D: requirement -> use case -> analysis/design diagram -> code file and line on GitHub -> table -> test, for five use cases (UC02 search by keyword, UC04 search by image, UC07 checkout, UC11 cancel order, UC13 update order status); 320 line links checked against the current files, 0 wrong; essay traceability tables in Ch. 2 and Ch. 4) |
| R14 | Defense showcase | Sections A-G, links to artefacts | Guideline 11 | Defense | `showcase/index.html` | Every link checked | PASS (tools/build_showcase.py; 291 local links and 44 anchors resolve, 0 broken; line links open after the push to github.com/scalliontor/Hoa) |
| R15 | Defense guide | 5-7 min script, design decisions, likely questions | Guideline 12 | Defense | `guide/` (Vietnamese) | Based on the real product | PASS (guide/guide_thuyet_trinh_Hoa.pdf, 20 pages, built 11/11 23:50 with 0 overfull: 7-step script of about 6 minutes following showcase A-G with the window to open and the one thing to point at, a 3-minute version, 10 design decisions, 25 questions in 9 groups, live demo flows with and without Gemma, the manual VP Generate Database steps, troubleshooting, question -> file/diagram appendix; counts and code line numbers are read from the project at build time; the 17 VP diagram names it quotes exist in the .vpp; demo facts checked: order 20261003 belongs to C002, C001's cart holds P03 at 89 USD, the category label sits above the painting title; DeepInfra availability check answers 200) |
| R16 | Native VP | Project opens in VP; edition limits stated | Guideline 5.2 | all | `vp/tieuluan_design.vpp` (40 diagrams) | Opens; CE exports clean; trial ones labelled | PASS (vp/tieuluan_design.vpp: 40 diagrams, names checked by tools/build_vp.py; CE SVGs without watermark; the 6 BPMN/ArchiMate/DFD figures are window screenshots titled "Evaluation Copy" and labelled as trial in the essay and showcase) |

## Diagram inventory (target)

| Phase | Diagram | VP id | Tool | Status |
|---|---|---|---|---|
| Requirements | Context (DFD level 0) | c1_dfd0 | VP trial (screenshot) | done |
| Requirements | Stakeholder map (ArchiMate) | c1_stakeholders | VP trial (screenshot) | done |
| Requirements | Business process (BPMN) | c1_process | VP trial (screenshot) | done |
| Requirements | Problem tree (ArchiMate) | c1_problems | VP trial (screenshot) | done |
| Requirements | Use case overview + 3 detail | c1_usecase, c2_uc_search, c2_uc_purchase, c2_uc_assistant_admin | VP CE | done |
| Analysis | DFD level 1 | c2_dfd1 | VP trial (screenshot) | done |
| Analysis | Activity x6 | c2_activity_search, _image, _checkout, _cancel, _admin, _products | VP CE | done |
| Analysis | Analysis sequence (BCE) x3 | c2_bce_search, _checkout, _cancel | VP CE | done |
| Analysis | Voice sequence (A06) and order state machine | c2_seq_voice, c2_state_order | VP CE | done |
| Analysis | Analysis class diagram | c2_domain | VP CE | done (with Category) |
| Data | Conceptual / logical / physical / ERD | c42_conceptual, c42_orm, c42_tables, c42_erd | VP CE | done (with category) |
| Design | Three logical components | c44_components | VP CE | done |
| Design | Design classes, layers, packages | c43_design, c44_layers, c44_classes, c44_classes_backend, c44_packages | VP CE | done (with Category, DetailKind) |
| Design | Design sequences | c44_checkout_seq, c44_seq_search, c44_seq_cancel (+ c3_seq_image, c3_seq_assistant) | VP CE | done |
| Code | Deployment | c5_deployment | VP CE | done |

## Plan to 12/11 18:00 (each unit ends with a check)

| Unit | Window | Work | Check |
|---|---|---|---|
| U1 | 22:30-00:30 | Category in the specification (`tools/model.py`): analysis class, design class, table, FKs; essay text | `gen_sql.py` builds the schema; model loads |
| U2 | 00:30-03:00 | Diagrams follow the model: analysis, data models, design classes, ERD; new three-component diagram; VP rebuild | `build_vp.py --check` clean, PNGs inspected, project holds every diagram |
| U3 | 03:00-06:00 | Code: schema, seed, repository, domain, browse by category in the UI; behaviour tests | `demo/test.sh` passes, `check_code_model.py` all match, server runs |
| U4 | 06:00-08:00 | VP database generation from the physical model (trial GUI) with screenshots; DDL compared with the schema | comparison script output saved |
| U5 | 08:00-10:00 | Essay: Ch. 2 and Ch. 4 for Category, generation, components; traceability | report builds clean |
| U6 | 10:00-13:00 | Showcase A-G, every link verified | link checker, Playwright desktop + mobile |
| U7 | 13:00-15:00 | E2E run of the demo script with evidence; defense guide (5-7 min, decisions, questions) | e2e log, guide PDF |
| U8 | 15:00-18:00 | Buffer, final acceptance table, rehearsal | this file updated with evidence |

## Risks

| Risk | Effect | Action |
|---|---|---|
| Self-hosted Gemma server down (nginx 502 since 11/11 22:38) | Resolved: the demo uses Gemma 4 31B at DeepInfra (key only in demo/config/app.local.properties); only configuration changed | If DeepInfra fails during the defense, show the fallback on purpose (NFR02, NFR12); Chapter 3 numbers were measured on the self-hosted server |
| VP trial ends (30 days from 5/11) | Trial-only diagrams cannot be reopened in the GUI | Screenshots and the .vpp are kept; the CE opens every UML/ERD diagram |

If time runs short: keep U1-U3 and U6 complete; reduce U4 to exact manual steps with the DDL VP writes; shorten U7.
