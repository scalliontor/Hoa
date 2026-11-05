# figures/vp: Visual Paradigm figures

Every figure here is a PNG (3x, used by the slides), a vector PDF (used by the report) and an SVG exported from the
editable Visual Paradigm 18.1 project
`vp/tieuluan_design.vpp`. All names (classes, operations, tables, use cases) come from `tools/model.py`.
The figures use VP's default style. Every label is placed explicitly so that no text touches a shape,
a line or other text, and every PNG was checked by eye after export.

Rebuild: `python3 tools/build_vp.py` (about 25 s; VP runs headless; PyMuPDF crops each PDF to the diagram).
The current exports were made while VP ran as an evaluation copy, so they carry VP's evaluation watermark; a run
with an activated Community Edition replaces it with the small "Powered by" footer. `python3 tools/build_vp.py --check`
runs only the geometric self-check of the layouts. Layouts live in `tools/vp_diagrams/ch1.py` ... `ch5.py`
(shared helpers in `common.py`; the five class models share one grid in `classmodel.py`).

| id | Chapter | What it shows |
|---|---|---|
| c1_context | 1 Requirement Determination (1.7) | Context diagram: the Họa. Gallery system as one box; Customer, Administrator, Payment Service and Gemma 4 Service with the «flow» of information in each direction |
| c1_usecase | 2 Analysis (2.4) | Use case diagram: 4 actors, UC01–UC14 inside the Họa. Gallery boundary; generalization of the search use cases, «Include» UC07→UC06, UC10→UC01, UC10→UC09, «Extend» UC05→UC01, UC11→UC08; supporting actors on the right; no crossing actor lines |
| c2_domain | 2 Analysis (2.8) | Domain model drawn as the analysis class diagram: the 17 classes with their attributes; relationships by kind only (association, composition, aggregation, generalization, «create» from Cart to Order), no names, no multiplicities |
| c2_activity_checkout | 2 Analysis | Checkout activity in three swimlanes (Customer / Họa. system / Database): cart and stock checks with guards, order creation, saving orders, order_item, payment and shipping in one transaction, then decreasing stock and clearing the cart |
| c2_activity_search | 2 Analysis | Multimodal search activity (Customer / Họa. system / Gemma 4 Service): text, voice (self-hosted Whisper) or photo, Gemma 4 understands the query, fallback to keyword rules (NFR02), retrieve, rank with S = α·Stext + β·Simage + γ·Sbusiness, results with reasons or an empty state |
| c2_seq_voice | 2 Analysis | A06 voice-search sequence with exactly the 7 participants Customer, SearchUI, SpeechService, QueryService, SearchService, ProductRepository, RankingService (the customer checks the transcript before submitVoice) |
| c2_state_order | 2 Analysis | Order state machine: PLACED → PROCESSING → SHIPPED → DELIVERED with advanceTo(), cancel() from PLACED or PROCESSING to CANCELLED |
| c3_ai_architecture | 3 AI in e-commerce | AI components: AssistantService, SearchService, QueryService, ImageService, RankingService, VectorIndex, the LlmClient «Interface» with GemmaClient, LlmReply, ToolCall; SpeechService → SpeechClient «Interface» ← WhisperClient; notes on the Gemma 4 server and the local Whisper server |
| c3_seq_image | 3 AI in e-commerce | Search by image: Customer, ImageUpload, SearchUI, SearchController, SearchService, ImageService, GemmaClient, VectorIndex, RankingService; alt [Gemma 4 replies] / [error or timeout → empty vector] |
| c3_seq_assistant | 3 AI in e-commerce | Shopping assistant with tool calling: Customer, AssistantView, AssistantController, AssistantService, GemmaClient, OrderService, OrderRepository; opt [Gemma 4 asks for a tool] with the ownership check isOwnedBy(customerId) |
| c41_analysis | 4 Design (4.1) | Analysis class diagram: the 17 classes with attributes; relationships by kind only, no names, no multiplicities, no ORM (they are added in the data model) |
| c42_conceptual | 2 Analysis (2.9.1) | Conceptual data model: the 17 entities by name only and the named links between them (no attributes, no multiplicities); generalizations kept |
| c42_orm | 2 Analysis (2.9.2) | Logical data model: the 17 classes with attributes as «ORM-Persistable», named associations with multiplicities; each generalization becomes a 1 – 0..1 "is a" association |
| c42_tables | 4 Design (4.2.1) | Physical data model: the 17 tables as «table» classes with SQL types and {PK, FK, U, NULL}; every foreign key labelled "name (column)" with multiplicities |
| c42_erd | 4 Design (4.2.2) | Database as a VP entity relationship diagram (the orange tables) on the grid of the physical data model: every column with type, PK/FK icons, N (nullable) and U (unique), crow's-foot foreign keys with their names |
| c43_design | 4 Design (4.3) | Design class diagram of the domain: 20 classes with typed attributes and operations, 3 enumerations, navigable associations with role names, «use» OrderItem → CartItem |
| c44_layers | 4 Design (4.4.1) | The three layers (Presentation, Application, Data) as frames with their classes inside and the «use» / realization links inside each layer and to the layer below; a note names the few long links left out and the shared domain model |
| c44_classes | 4 Design (4.4) | Presentation → application → domain, one vertical slice per feature (views, controllers, services, Cart and Order), «use» and «create» dependencies; a note explains how WebServer dispatches to the controllers |
| c44_classes_backend | 4 Design (4.4) | Application → data (persistence): the four services and the repository «Interface»s with their methods, their SQLite implementations (realization) and Database |
| c44_checkout_seq | 4 Design (4.4/4.5) | Checkout design sequence across the layers (slide A05): CheckoutController → CheckoutService → Order and the repositories, with a loop over the cart items |
| c5_deployment | 5 Code | Deployment: demo laptop (web browser, Java 17 runtime with hoa-demo on :8686, ecom.db, Python voice server 127.0.0.1:9000 with faster-whisper) and the L40S GPU server (Nginx :8000 → vLLM serving Gemma 4) |

`c42_erd` exports since the caption box of each table is set to one line; without it VP CE keeps a tall default
header and clips the columns. The layer frames of `c44_layers` are transparent, otherwise VP CE draws them over the
classes placed on them.

Known compromise: `c44_classes_backend` has one unavoidable crossing (CheckoutService → ProductRepository passes
over CartService → CartRepository at a right angle). No label touches it.
