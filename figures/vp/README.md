# figures/vp: Visual Paradigm figures

Every figure here is a PNG (3x, used by the slides), a vector PDF (used by the report) and an SVG exported from the
editable Visual Paradigm 18.1 project
`vp/tieuluan_design.vpp`. All names (classes, operations, tables, use cases) come from `tools/model.py`.
The figures use VP's default style. Every label is placed explicitly so that no text touches a shape,
a line or other text, and every PNG was checked by eye after export.

Rebuild: `python3 tools/build_vp.py` (a few minutes; PyMuPDF crops each PDF to the diagram).
`python3 tools/build_vp.py --check` runs only the geometric self-check of the layouts, and
`python3 tools/build_vp.py --only id1,id2 --out DIR` test-builds some diagrams into DIR without touching this folder.
Layouts live in `tools/vp_diagrams/ch1.py` ... `ch5.py` and `x_*.py` (shared helpers in `common.py`; the five class
models share one grid in `classmodel.py`).

Two editions of VP 18.1 are used:
- **Community Edition** for every UML and ERD figure: PNG (3x), cropped vector PDF and SVG, with VP's small
  "Powered by Visual Paradigm Community Edition" footer and no watermark.
- **Enterprise edition, 30-day trial** for the BPMN, ArchiMate and DFD figures, which the Community Edition refuses
  to draw. Its exports carry an "evaluation copy" watermark, so these figures are screenshots of the VP window
  instead (title bar "Visual Paradigm Enterprise (Evaluation Copy)"), taken by `tools/vp_shots.py` with the plugin in
  `vp/shots_plugin`. They exist only as PNG, and every caption in the essay says that they come from the trial.
  The trial edition also saves the complete project, so `vp/tieuluan_design.vpp` holds every diagram.
  Since 12/11/2026 the trial refuses to reopen saved projects ("Evaluation on this project has been expired"); the
  Community Edition opens `vp/tieuluan_design.vpp` with all 40 diagrams.

Two more trial screenshots are not diagrams but VP's own **Generate Database** wizard on the ERD, made by
`tools/vp_generate_db.py` (Chapter 4.2.3, showcase section E): `c42_generate_db.png` (the wizard: SQLite, Create
Database, Generate DDL, output folder) and `c42_generate_db_done.png` (after OK: "Generate Database - Finish" and the
ORM messages). The DDL the wizard wrote is `demo/db/vp_wizard_ddl.sql`.

| id | Chapter | What it shows |
|---|---|---|
| c1_stakeholders | 1 Requirement Determination (1.3) | *Trial screenshot.* Stakeholder map in ArchiMate: the eight stakeholders, their concerns (drivers) and the goals of the system that answer them, with requirement ids |
| c1_process | 1 Requirement Determination (1.4) | *Trial screenshot.* Business process from order to delivery in BPMN: Customer pool, Họa. Gallery pool with Administrator and Warehouse staff lanes, Payment Service and Delivery carrier as black-box pools, message flows, card / cash gateway |
| c1_problems | 1 Requirement Determination (1.6) | *Trial screenshot.* Problem tree in ArchiMate: five root causes influence the problems P1-P5, which influence their impacts |
| c1_dfd0 | 1 Requirement Determination (1.7) | *Trial screenshot.* Context diagram as DFD level 0: process 0 Họa. Gallery, the four external entities and eight labelled flows |
| c2_dfd1 | 2 Analysis (DFD level 1) | *Trial screenshot.* DFD level 1, balanced with level 0: four processes, data stores D1 Paintings and artists, D2 Carts, D3 Orders, payments, shipping; customer and D1 drawn twice |
| c2_uc_search | 2 Analysis (2.4) | Use cases of search and discovery: abstract UC01 with UC02, UC03, UC04, UC14 as specialisations, UC05 «extend», Gemma 4 Service as supporting actor |
| c2_uc_purchase | 2 Analysis (2.4) | Use cases of cart, checkout and orders: UC07 «include» UC06, UC11 «extend» UC08, Payment Service supporting UC07 |
| c2_uc_assistant_admin | 2 Analysis (2.4) | Use cases of the assistant (UC10 «include» UC01 and UC09, Gemma 4 Service) and of the administrator (UC12, UC13) |
| c2_activity_image | 2 Analysis (UC04) | Activity of search by image (ACT-04): file check (BR10), Gemma description or local colour fallback (NFR02), retrieval, ranking, empty state |
| c2_activity_cancel | 2 Analysis (UC11) | Activity of cancel order (ACT-11): ownership check (BR08) and status check (BR06) |
| c2_activity_admin | 2 Analysis (UC13) | Activity of update order status (ACT-13): transition check against the order state machine (BR07) |
| c2_activity_products | 2 Analysis (UC12) | Activity of manage products (ACT-12): administrator session check, validation (A1), Category.accepts for a new painting (A4), save of product, painting and feature vector in one transaction |
| c44_components | 4 Design (4.4.1) | Three logical components: Presentation, Application and Data layers with one component per Java package, the shared domain model, the database file and the Gemma / Whisper services as external components, each dependency labelled with what crosses it |
| c2_bce_search | 2 Analysis (UC02) | Analysis sequence in boundary-control-entity style: SearchUI «boundary», SearchControl «control», Painting and Artist «entity»; alt ranked results / empty state |
| c2_bce_checkout | 2 Analysis (UC07) | Analysis sequence of checkout: CheckoutUI, CheckoutControl, Cart, Painting, Order, OrderItem, Payment; loop over the cart lines, alt out of stock / order created |
| c2_bce_cancel | 2 Analysis (UC11) | Analysis sequence of cancel order: OrderUI, CancelOrderControl, Order; alt not the customer's / shipped / already cancelled / cancel |
| c44_packages | 4 Design (4.4.1) | Package diagram: Presentation, Application and Data layers with their Java sub-packages and the shared Domain model, «use» dependencies downwards and to the domain |
| c44_seq_search | 4 Design (4.4) | Design sequence of UC02: SearchUI.submitText -> SearchController.search -> SearchService.searchText -> QueryService.textQuery (LlmClient, keyword-rule fallback) -> ProductRepository.allProducts, VectorIndex.build -> RankingService.rank |
| c44_seq_cancel | 4 Design (4.4) | Design sequence of UC11: OrderController.cancelOrder -> OrderService.cancelOrder/getOrder -> OrderRepository.findOrder, Order.isOwnedBy, Order.cancel(), OrderRepository.updateStatus |
| c1_context | 1 (kept for the slides) | Context diagram: the Họa. Gallery system as one box; Customer, Administrator, Payment Service and Gemma 4 Service with the «flow» of information in each direction |
| c1_usecase | 2 Analysis (2.4) | Use case diagram: 4 actors, UC01–UC14 inside the Họa. Gallery boundary; generalization of the search use cases, «Include» UC07→UC06, UC10→UC01, UC10→UC09, «Extend» UC05→UC01, UC11→UC08; supporting actors on the right; no crossing actor lines |
| c2_domain | 2 Analysis (2.8) | Domain model drawn as the analysis class diagram: the 18 classes (Category classifies Product) with their attributes; relationships by kind only (association, composition, aggregation, generalization, «create» from Cart to Order), no names, no multiplicities |
| c2_activity_checkout | 2 Analysis | Checkout activity in three swimlanes (Customer / Họa. system / Database): cart and stock checks with guards, order creation, saving orders, order_item, payment and shipping in one transaction, then decreasing stock and clearing the cart |
| c2_activity_search | 2 Analysis | Multimodal search activity (Customer / Họa. system / Gemma 4 Service): text, voice (self-hosted Whisper) or photo, Gemma 4 understands the query, fallback to keyword rules (NFR02), retrieve, rank with S = α·Stext + β·Simage + γ·Sbusiness, results with reasons or an empty state |
| c2_seq_voice | 2 Analysis | A06 voice-search sequence with exactly the 7 participants Customer, SearchUI, SpeechService, QueryService, SearchService, ProductRepository, RankingService (the customer checks the transcript before submitVoice) |
| c2_state_order | 2 Analysis | Order state machine: PLACED → PROCESSING → SHIPPED → DELIVERED with advanceTo(), cancel() from PLACED or PROCESSING to CANCELLED |
| c3_ai_architecture | 3 AI in e-commerce | AI components: AssistantService, SearchService, QueryService, ImageService, RankingService, VectorIndex, the LlmClient «Interface» with GemmaClient, LlmReply, ToolCall; SpeechService → SpeechClient «Interface» ← WhisperClient; notes on the Gemma 4 server and the local Whisper server |
| c3_seq_image | 3 AI in e-commerce | Search by image: Customer, ImageUpload, SearchUI, SearchController, SearchService, ImageService, GemmaClient, VectorIndex, RankingService; alt [Gemma 4 replies] / [error or timeout → empty vector] |
| c3_seq_assistant | 3 AI in e-commerce | Shopping assistant with tool calling: Customer, AssistantView, AssistantController, AssistantService, GemmaClient, OrderService, OrderRepository; opt [Gemma 4 asks for a tool] with the ownership check isOwnedBy(customerId) |
| c41_analysis | 4 Design (4.1) | Analysis class diagram: the 18 classes with attributes, Category included; relationships by kind only, no names, no multiplicities, no ORM (they are added in the data model) |
| c42_conceptual | 2 Analysis (2.9.1) | Conceptual data model: the 18 entities by name only and the named links between them (no attributes, no multiplicities); generalizations kept |
| c42_orm | 2 Analysis (2.9.2) | Logical data model: the 18 classes with attributes as «ORM-Persistable», named associations with multiplicities; each generalization becomes a 1 – 0..1 "is a" association |
| c42_tables | 4 Design (4.2.1) | Physical data model: the 18 tables as «table» classes (category, product with category_id, painting and frame detail tables) with SQL types and {PK, FK, U, NULL}; every foreign key labelled "name (column)" with multiplicities |
| c42_erd | 4 Design (4.2.2) | Database as a VP entity relationship diagram (the orange tables) on the grid of the physical data model: every column with type, PK/FK icons, N (nullable) and U (unique), crow's-foot foreign keys named after their constraints, fk_<table>_<column> (model.fk_name; Generate Database needs them unique) |
| c43_design | 4 Design (4.3) | Design class diagram of the domain: 18 classes with typed attributes and operations (Category with accepts()) and 4 enumerations (DetailKind among them), navigable associations with role names, «use» OrderItem → CartItem |
| c44_layers | 4 Design (4.4.1) | The three layers (Presentation, Application, Data) as frames with their classes inside and the «use» / realization links inside each layer and to the layer below; a note names the few long links left out and the shared domain model |
| c44_classes | 4 Design (4.4) | Presentation → application → domain, one vertical slice per feature (views, controllers, services, Cart and Order), «use» and «create» dependencies; a note explains how WebServer dispatches to the controllers |
| c44_classes_backend | 4 Design (4.4) | Application → data (persistence): the four services and the repository «Interface»s with their methods, their SQLite implementations (realization) and Database |
| c44_checkout_seq | 4 Design (4.4/4.5) | Checkout design sequence across the layers (slide A05): CheckoutController → CheckoutService → Order and the repositories, with a loop over the cart items |
| c5_deployment | 5 Code | Deployment: demo laptop (web browser, Java 17 runtime with hoa-demo on :8686, ecom.db, Python voice server 127.0.0.1:9000 with faster-whisper) and the Gemma 4 service at DeepInfra (OpenAI-compatible API; a self-hosted L40S/vLLM server until 11/11/2026) |

`c42_erd` exports since the caption box of each table is set to one line; without it VP CE keeps a tall default
header and clips the columns. The layer frames of `c44_layers` are transparent, otherwise VP CE draws them over the
classes placed on them.

Known compromise: `c44_classes_backend` has one unavoidable crossing (CheckoutService → ProductRepository passes
over CartService → CartRepository at a right angle). No label touches it.
