# Họa. — the demo shop of the essay

Họa. sells museum-quality prints of public-domain paintings and the frames to go with them. The code is the
design of Chapter 4 made real: the 60 Java classes and 9 browser views of `tools/model.py` with the same names,
fields and operations, and the 18 tables of section 4.2. It is plain Java 17 with no framework (the JDK
HTTP server, JDBC on SQLite, Gson). Two AI services are used:

* **Gemma 4** on the course server (`171.226.10.121:8000`, OpenAI-compatible API) reads search requests, looks at
  photos (paintings and rooms), picks paintings for a room and runs the shopping assistant with tool calling;
* **Whisper** (`voice-server/`, self-hosted on this computer) turns spoken requests into text.

Everything except the Gemma calls works offline, and every AI feature has a fallback when Gemma is not reachable
(keyword rules, local colour reading, rule-based assistant; NFR02).

## Run

First time on a new computer, create `config/app.local.properties` (it is not in git) with the Gemma key from
`HUONG_DAN_GOI_GEMMA4.md`:

```
gemma.apiKey=<the key>
```

Without it the shop still runs, but every Gemma call fails and the offline fallbacks answer instead. The first
`./run.sh` also creates the Whisper virtual environment and downloads the model, so it needs the Internet once.

```bash
./build.sh                    # compile into build/classes (needs a JDK 17+, e.g. brew install openjdk@21)
./run.sh                      # start the Whisper server and the shop: http://127.0.0.1:8686
./test.sh                     # 66 tests and the code-model check -> ../build/test_results.txt
python3 scripts/evaluate.py   # the A06-style evaluation -> ../build/eval/
```

To show that every AI feature has a fallback, start a second shop whose Gemma address leads nowhere:
`./run.sh config/app.offline.properties` (port 8687, its own database `data/ecom_offline.db`).

Demo accounts (switcher in the top bar): **C001** Nguyen Minh An (VIP, 10 % discount, orders 20261001 and
20261002), **C002** Tran Thu Binh (new customer, order 20261003) and **ADMIN** (manage paintings and order
status). The database `data/ecom.db` is created from `db/` at the first start; delete it to start again from the
seed data. Settings (port, database, Gemma, Whisper, ranking weights α, β, γ) are in `config/app.properties`.
The JSON API is described with real examples in [API.md](API.md).

## Folders

| Folder | Contents | Report |
|---|---|---|
| `src/main/java/com/ptit/ecom/` | the application: three layers (presentation, application, data = `infrastructure.*`) and the shared domain model (table below) | 4.4, 4.5, 5 |
| `web/` | the browser UI: `index.html`, `css/`, `js/` (one file per view of the model: `search-ui.js`, `voice-input.js`, `room-preview.js`, …), `img/` (painting images, sample rooms, `credits.json`) | 5 |
| `db/` | `ecom_schema_sqlite.sql` and `seed.sql`, generated from `TABLES` by `tools/gen_sql.py` | 4.2 |
| `data/` | `catalog.json` (32 paintings, 5 frames, artists), `ATTRIBUTION.md` (Wikimedia Commons sources), `eval_images/` (photos for the evaluation); `ecom.db` and logs at run time | 3, 5 |
| `config/` | `app.properties` | 5 |
| `lib/` | `sqlite-jdbc`, `gson`, `slf4j` — the only libraries | 5 |
| `tests/java/` | 66 tests without a framework (`TestRunner`), fake Gemma and Whisper clients | 5 |
| `scripts/` | `java_home.sh` (finds the JDK), `evaluate.py` (experimental evaluation) | 3, 5 |
| `generated/` | the skeleton of section 4.5, generated from the model by `tools/gen_java.py`; the application was started from it | 4.5 |
| `voice-server/` | the self-hosted Whisper server (own README) | 3, 5 |

## Package map

| Package | Layer (4.4) | Classes | Slide concept | Report |
|---|---|---|---|---|
| `presentation.view` (`web/js/*.js`) | Presentation | SearchUI, VoiceInput, RoomPreview, ImageUpload, SearchResultView, CartView, OrderView, AssistantView, AdminView | A06 presentation layer (search UI, voice input, image upload, result view) | 4.4, 5 |
| `presentation.controller` | Presentation | SearchController, CartController, CheckoutController, OrderController, AdminController, AssistantController | A05 `CheckoutController` | 4.4, 4.5 |
| `presentation.web` | Presentation | WebServer, SessionManager, EcomApplication | A06 `main.py` (composition root), HTTP routes | 4.4, 5 |
| `application.service` | Application | CartService, CheckoutService, OrderService, ProductService, AssistantService, AssistantReply | A05 `CheckoutService.checkout(cartId, …)` | 4.4, 4.5 |
| `application.search` | Application | SearchService, QueryService, SpeechService, ImageService, RankingService, CommonQuery, SearchResult | A06 search engine: query understanding, S = α·Stext + β·Simage + γ·Sbusiness | 3, 4.4 |
| `domain.customer` | Domain model (shared) | Customer, CustomerVIP, CustomerNew, FullName, Address | analysis classes of 4.1 | 4.1, 4.3 |
| `domain.product` | Domain model (shared) | Category, DetailKind, Product, Painting, Frame, Artist | | 4.1, 4.3 |
| `domain.cart` | Domain model (shared) | Cart, CartItem | | 4.3 |
| `domain.order` | Domain model (shared) | Order, OrderItem, OrderStatus, Shipping, ShippingStatus | | 4.3 |
| `domain.payment` | Domain model (shared) | Payment, PayCash, PayCredit, PaymentStatus | polymorphic `process()` | 4.3 |
| `infrastructure.repository` | Data | CustomerRepository, ProductRepository, CartRepository, OrderRepository | A05 repositories | 4.4 |
| `infrastructure.repository.sqlite` | Data | Database, SqliteCustomerRepository, SqliteProductRepository, SqliteCartRepository, SqliteOrderRepository | A06 product and order databases | 4.2, 4.4 |
| `infrastructure.search` | Data | VectorIndex | A06 vector database, `cosine_similarity` | 3, 4.4 |
| `infrastructure.ai` | Data | LlmClient, GemmaClient, LlmReply, ToolCall, SpeechClient, WhisperClient | Gemma 4 and Whisper behind interfaces | 3, 4.4 |

Dependencies point downwards only (Presentation → Application → Domain / Infrastructure → Domain);
controllers return domain objects, and only `EcomApplication` creates the infrastructure objects.
`python3 ../tools/check_code_model.py` checks all of this against the model.
