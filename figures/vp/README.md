# figures/vp: Visual Paradigm figures

Every figure here is a PNG (2x) and an SVG exported from the editable Visual Paradigm 18.1 project
`vp/tieuluan_design.vpp`. All names (classes, operations, tables, use cases) come from `tools/model.py`.
The figures use VP's default style. Every label is placed explicitly so that no text touches a shape,
a line or other text, and every PNG was checked by eye after export.

Rebuild: `python3 tools/build_vp.py` (about 25 s; VP runs headless). `python3 tools/build_vp.py --check`
runs only the geometric self-check of the layouts. Layouts live in `tools/vp_diagrams/ch1.py` ... `ch5.py`
(shared helpers in `common.py`; the five class models share one grid in `classmodel.py`).

| id | Chapter | What it shows |
|---|---|---|
| c1_context | 1 Requirement Determination | Context view: the Họa. Gallery system as one box; Customer, Administrator, Payment Service and Gemma 4 Service with the «flow» of information in each direction |
| c1_usecase | 1 Requirement Determination | Use case diagram: 4 actors, UC01–UC14 inside the Họa. Gallery boundary; generalization of the search use cases, «Include» UC07→UC06, UC10→UC01, UC10→UC09, «Extend» UC05→UC01, UC11→UC08; supporting actors on the right; no crossing actor lines |
| c2_domain | 2 Analysis | Domain model: the 17 concepts (names only), associations with names and multiplicities, generalizations, «create» checkout from Cart to Order |
| c2_activity_checkout | 2 Analysis | Checkout activity in three swimlanes (Customer / Họa. system / Database): cart and stock checks with guards, order creation, saving orders, order_item, payment and shipping in one transaction, then decreasing stock and clearing the cart |
| c2_activity_search | 2 Analysis | Multimodal search activity (Customer / Họa. system / Gemma 4 Service): text, voice (self-hosted Whisper) or photo, Gemma 4 understands the query, fallback to keyword rules (NFR02), retrieve, rank with S = α·Stext + β·Simage + γ·Sbusiness, results with reasons or an empty state |
| c2_seq_voice | 2 Analysis | A06 voice-search sequence with exactly the 7 participants Customer, SearchUI, SpeechService, QueryService, SearchService, ProductRepository, RankingService (the customer checks the transcript before submitVoice) |
| c2_state_order | 2 Analysis | Order state machine: PLACED → PROCESSING → SHIPPED → DELIVERED with advanceTo(), cancel() from PLACED or PROCESSING to CANCELLED |
| c3_ai_architecture | 3 AI in e-commerce | AI components: AssistantService, SearchService, QueryService, ImageService, RankingService, VectorIndex, the LlmClient «Interface» with GemmaClient, LlmReply, ToolCall; SpeechService → SpeechClient «Interface» ← WhisperClient; notes on the Gemma 4 server and the local Whisper server |
| c3_seq_image | 3 AI in e-commerce | Search by image: Customer, ImageUpload, SearchUI, SearchController, SearchService, ImageService, GemmaClient, VectorIndex, RankingService; alt [Gemma 4 replies] / [error or timeout → empty vector] |
| c3_seq_assistant | 3 AI in e-commerce | Shopping assistant with tool calling: Customer, AssistantView, AssistantController, AssistantService, GemmaClient, OrderService, OrderRepository; opt [Gemma 4 asks for a tool] with the ownership check isOwnedBy(customerId) |
| c41_analysis | 4 Design (4.1) | Analysis class diagram: the 17 classes with attributes, associations, multiplicities, generalizations |
| c42_orm | 4 Design (4.2) | Data model: the 17 classes as «ORM-Persistable»; each generalization becomes a 1 – 0..1 "is a" association |
| c42_tables | 4 Design (4.2) | Physical database: the 17 tables as «table» classes with types and {PK, FK, U, NULL}; every foreign key labelled "name (column)" with multiplicities |
| c43_design | 4 Design (4.3) | Design class diagram of the domain: 20 classes with typed attributes and operations, 3 enumerations, navigable associations with role names, «use» OrderItem → CartItem |
| c44_layers | 4 Design (4.4) | The four layer packages (presentation, application, domain, infrastructure) with their Java sub-packages and the «use» dependencies between layers; classes are owned by these packages in the model |
| c44_classes | 4 Design (4.4) | Presentation → application → domain, one vertical slice per feature (views, controllers, services, Cart and Order), «use» and «create» dependencies; a note explains how WebServer dispatches to the controllers |
| c44_classes_backend | 4 Design (4.4) | Application → infrastructure (persistence): services, repository «Interface»s, their SQLite implementations (realization) and Database |
| c44_checkout_seq | 4 Design (4.4/4.5) | Checkout design sequence across the layers (slide A05): CheckoutController → CheckoutService → Order and the repositories, with a loop over the cart items |
| c5_deployment | 5 Code | Deployment: demo laptop (web browser, Java 17 runtime with hoa-demo on :8686, ecom.db, Python voice server 127.0.0.1:9000 with faster-whisper) and the L40S GPU server (Nginx :8000 → vLLM serving Gemma 4) |

The project also contains `c42_erd`, a VP entity relationship diagram of the same 17 tables for VP's database
tools. It is not exported, because headless export clips the entity columns; the database figure is `c42_tables`.

Known compromise: `c44_classes_backend` has one unavoidable crossing (CheckoutService → ProductRepository passes
over CartService → CartRepository at a right angle). No label touches it.
