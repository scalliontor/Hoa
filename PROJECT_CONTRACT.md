# Họa. — hợp đồng chung giữa báo cáo, demo, sơ đồ VP và slide

Sản phẩm: **Họa.** — cửa hàng tranh trực tuyến (bản in tranh danh họa đã thuộc phạm vi công cộng + khung tranh),
có tìm kiếm đa phương thức (chữ, giọng nói, ảnh) và trợ lý mua sắm dùng **Gemma 4**. Thiết kế giao diện tham khảo
https://fustic.studio (nền đen, lưới chấm, tiêu đề sans lớn chữ mảnh, nhãn monospace in hoa, ký hiệu ▪, thẻ ảnh lớn,
nút viền "XEM TẤT CẢ", footer có wordmark khổng lồ "Họa.", nút đổi sáng/tối).

## LANGUAGE AND STYLE RULES (latest user feedback — overrides anything below)
- **Everything in English**: report (all 5 chapters, cover, captions "Figure x.y" / "Table x.y"), slides and speaker
  notes, demo UI, catalog data (titles, styles, colours), Gemma prompts and assistant answers, code comments,
  READMEs, VP diagram labels (lanes, guards, notes). Prices in **USD** (matches the A06 query "under 100 dollars").
- Demo queries (model.DEMO_QUERIES): "blue landscape paintings", "Monet paintings under 100 dollars",
  "show me paintings similar to this image", "find my order 20261001", "where is my latest order?".
- Voice: Whisper transcribes **English** (language=en by default, auto-detect allowed).
- VP diagrams: **simple, VP default look** — no custom fill colours or decorations, few elements per diagram,
  generous spacing, straight/orthogonal connectors with explicit routes, use case extension-point compartments
  hidden; **no text may touch or overlap a shape, a line or other text** (place stereotype and guard labels
  explicitly). Every exported PNG must be inspected and fixed before it is delivered.

## Nguồn sự thật
- `tools/model.py`: yêu cầu (REQUIREMENTS), actor, use case, 17 lớp phân tích, 61 lớp thiết kế (54 Java + 7 view JS),
  quan hệ, layer, 17 bảng. Tên lớp/phương thức/bảng ở mọi nơi phải đúng như file này.
- Chỉ agent DEMO được sửa chữ ký trong `DESIGN` khi bắt buộc; mọi thay đổi ghi vào `build/MODEL_CHANGES.md`.
- Tên theo slide môn học: A05 (CheckoutController → CheckoutService.checkout(cartId…) → CartRepository/OrderRepository),
  A06 (SearchUI, VoiceInput, ImageUpload, SearchResultView; QueryService.textQuery/voiceQuery/imageQuery;
  SpeechService.transcribe; ImageService; SearchService.searchText; RankingService S = α·Stext + β·Simage + γ·Sbusiness;
  ProductRepository.allProducts; OrderRepository.findOrder; VectorIndex.cosineSimilarity).

## Quy tắc đặt tên (bắt buộc)
- Tên lớp, tên phương thức, tên tham số, tên thuộc tính/biến thành viên trong Java và tên hàm trong JS
  phải **giống hệt** `DESIGN` trong model.py (không đổi, không viết tắt, không thêm public method ngoài thiết kế;
  hàm private phụ trợ thì được).
- Tên bảng, tên cột, khóa và ràng buộc trong SQLite phải **giống hệt** `TABLES` trong model.py; câu SQL trong
  repository chỉ dùng các bảng/cột đó.
- `tools/check_code_model.py` kiểm tra cả ba lớp: lớp/phương thức/tham số, thuộc tính, bảng/cột (DDL thật trong
  ecom.db và chuỗi SQL trong code) — báo cáo và slide chỉ trích tên đã qua kiểm tra.

## Bám slide môn học (INFOR-SYSTEM-ANAL-DESIGN/slide_01…05)
- Slide 01: IS = People + Processes + Data + Technology; Business Problem → Root Cause → Stakeholder Need → System
  Requirement; stakeholder analysis (goal, information need); business process (order processing + ngoại lệ);
  information catalogue; problem–cause–impact–need; system boundary + context view (Customer, Administrator,
  Payment Service, Gemma 4 Service).
- Slide 02: business/user/system requirements; FR/NFR; "Hệ thống phải + hành động + đối tượng + điều kiện";
  tiêu chí yêu cầu tốt; stakeholder ≠ actor; use case là mục tiêu, không phải nút bấm; bảng ID/Type/Priority/Source
  (REQUIREMENT_DETAILS); MoSCoW; traceability.
- Slide 03: use case spec (actor chính/phụ, goal, trigger, pre/post, main flow, ≥ 3 luồng thay thế cho use case
  chính; 4 use case khách + 2 use case vận hành = UC12, UC13); activity diagram có quyết định theo business rule;
  FR → UC → Scenario → ACT; kiểm tra nhất quán (hủy đơn trước khi giao = UC11).
- Slide 04 (A03): khái niệm miền, CartItem ≠ OrderItem, checkout là phép biến đổi, bội số.
- Slide 05 (A05): Controller / Service / Domain / Repository, CheckoutService.checkout, layer ≠ package,
  responsibility assignment, technology mapping, traceability.

## AI của sản phẩm (bắt buộc vì môn học về hệ thống có AI)
1. Tìm bằng câu chữ — Gemma 4 hiểu câu tự nhiên → bộ lọc (QueryService.textQuery).
2. Tìm bằng giọng nói — **Whisper tự host** (faster-whisper, chạy trên máy, âm thanh không rời máy) →
   bản ghi hiện ra cho khách sửa → QueryService.voiceQuery. Không làm TTS.
3. Tìm bằng ảnh — Gemma 4 vision mô tả ảnh (trường phái, chủ đề, màu) → VectorIndex.toVector → cosine.
4. Treo thử cho phòng (UC14) — Gemma 4 đọc ảnh căn phòng (tông màu, phong cách) → SearchService.searchRoom →
   RoomPreview đặt tranh lên ảnh tường.
5. Trợ lý giám tuyển — chat chữ hoặc giọng nói (Whisper), Gemma 4 tool calling (tìm tranh, tra đơn).

### API server giọng nói (`demo/voice-server`, agent VOICE)
- `GET  http://127.0.0.1:9000/health` → `{"ok": true, "model": "...", "device": "..."}`
- `POST http://127.0.0.1:9000/transcribe?language=vi` — body là byte âm thanh (webm/opus, mp4/aac, wav, aiff;
  `Content-Type` tương ứng) → `{"text": "...", "language": "vi", "duration": 3.2, "seconds": 0.9, "model": "..."}`
- Lỗi → HTTP 4xx/5xx với `{"error": "..."}`. Java gọi qua `WhisperClient` (interface `SpeechClient`); server tắt →
  `SpeechService.transcribe` trả null và giao diện mời khách gõ chữ.

## Tổ chức thư mục (để đọc báo cáo là tìm được file)
- Mỗi thư mục lớn có `README.md` ngắn nói nó chứa gì và ứng với chương nào của báo cáo.
- Chú thích hình trong báo cáo ghi tên sơ đồ VP (`figures/vp/<id>`); code trích ghi đường dẫn file thật.
- Báo cáo có phụ lục "Bản đồ thư mục" (chương/hình/bảng → đường dẫn). Cuối cùng tôi tạo `README.md` gốc và chuyển
  đồ cũ (chapter4/, code/, PDF design_04) vào `_archive/`.

## Thư mục và chủ sở hữu (không sửa thư mục của agent khác)
| Agent | Sở hữu |
|---|---|
| VOICE | `demo/voice-server/**`, `build/eval/voice_*` |
| FRONTEND | `demo/web/**` except `demo/web/img/**`; UI screenshots in `figures/demo/` (all except db_tables, db_rows) |
| REPORT-B | `report/chapters/ch3_ai.tex`, `report/chapters/ch4_design.tex` (REPORT keeps all other report files) |
| DEMO | `demo/**` (trừ `demo/voice-server`), `tools/gen_java.py`, `tools/gen_sql.py`, `tools/check_code_model.py`, `tools/fetch_paintings.py`, `db/**`, `figures/demo/**`, `build/excerpts5/**`, `build/eval/**`, `build/code_tree5.txt`, `build/code_stats5.tex`, `build/test_results.txt`, `build/MODEL_CHANGES.md` |
| VP | `tools/diagrams.py`, `tools/build_vp.py`, `vp/**`, `figures/vp/**` |
| REPORT | `report/**`, `build/report/**` |
| SLIDES | `slides/**` |

## Hình VP (`figures/vp/<id>.png` + `.svg`, agent VP)
| id | Nội dung | Chương |
|---|---|---|
| c1_context | Context view (slide 01): hệ thống "Họa. Gallery" ở giữa; Customer, Administrator, Payment Service, Gemma 4 Service với luồng thông tin chính | 1 |
| c1_usecase | Use case: 4 actor (Customer, Administrator, Gemma 4 Service, Payment Service); UC01–UC13 theo USE_CASES, USE_CASE_LINKS, SUPPORTING_ACTORS; ranh giới "Họa. Gallery" | 1 |
| c2_domain | Mô hình miền: 17 lớp chỉ tên + quan hệ, bội số | 2 |
| c2_activity_checkout | Activity có swimlane (Khách hàng / Hệ thống Họa. / CSDL) cho Checkout | 2 |
| c2_activity_search | Activity tìm kiếm đa phương thức: chọn chữ/giọng/ảnh → truy vấn chung → lấy ứng viên → xếp hạng; nhánh Gemma lỗi → luật từ khóa | 2 |
| c2_seq_voice | Sequence tìm bằng giọng nói đúng 7 participant của đề A06 (Customer, SearchUI, SpeechService, QueryService, SearchService, ProductRepository, RankingService) | 2 |
| c2_state_order | State machine của Order: PLACED → PROCESSING → SHIPPED → DELIVERED, CANCELLED | 2 |
| c3_ai_architecture | Lớp AI: SearchService, QueryService, ImageService, AssistantService, RankingService, VectorIndex, LlmClient «interface», GemmaClient, LlmReply, ToolCall + note máy chủ Gemma 4 | 3 |
| c3_seq_image | Sequence tìm bằng ảnh: Customer, ImageUpload, SearchUI, SearchController, SearchService, ImageService, GemmaClient, VectorIndex, RankingService | 3 |
| c3_seq_assistant | Sequence trợ lý tool calling: Customer, AssistantView, AssistantController, AssistantService, GemmaClient, OrderService, OrderRepository | 3 |
| c41_analysis | Sơ đồ lớp phân tích (17 lớp, thuộc tính) | 4 |
| c42_orm | Data model ORM-Persistable | 4 |
| c42_tables | Mô hình CSDL vật lý (17 bảng «table», PK/FK/U/NULL) | 4 |
| c43_design | Sơ đồ lớp thiết kế (lớp miền + 3 enum) | 4 |
| c44_layers | 4 layer + package con | 4 |
| c44_classes | Lớp theo tầng + use/create/realization | 4 |
| c44_checkout_seq | Sequence checkout qua các tầng | 4 |
| c5_deployment | Triển khai: Laptop (Trình duyệt, ứng dụng Java, ecom.db) ↔ máy chủ L40S (Nginx :8000, vLLM Gemma 4) | 5 |

## Ảnh chụp demo (`figures/demo/<name>.png`, agent DEMO, chụp bằng Playwright)
home, search_text, search_voice, search_image, product_detail, cart, checkout, orders, order_forbidden,
order_cancel, assistant, ai_fallback, room_preview, admin_products, admin_orders, db_tables, db_rows.

## Code trích cho Chương 5 (`build/excerpts5/<name>.java|.js`, ≤ 45 dòng, chép từ code thật)
EcomApplication, WebServer_routes, SearchService, QueryService, ImageService, VectorIndex, RankingService,
GemmaClient, AssistantService, CheckoutService, OrderService, SqliteOrderRepository, search_ui (js), voice_input (js).
Kèm `build/code_tree5.txt`, `build/code_stats5.tex` (macro \javaFileCount, \javaLineCount, \jsFileCount, \testCount),
`build/test_results.txt`, `build/eval/eval_summary.txt` + `eval_results.json` (đánh giá theo đề A06: số truy vấn,
số đúng, tỉ lệ thành công, ví dụ sai — cho chế độ text, voice, image, order).

## Dữ liệu demo
- Khách: C001 Nguyễn Minh An (VIP, giảm 10%), C002 Trần Thu Bình (khách mới). Đăng nhập demo bằng chọn tài khoản.
- Đơn mẫu: 20261001 (C001, SHIPPED), 20261002 (C001, DELIVERED), 20261003 (C002, PLACED).
- Giá: VND. Ảnh tranh: Wikimedia Commons, chỉ tác phẩm "Public domain", lưu `demo/web/img/`, ghi nguồn trong `demo/data/ATTRIBUTION.md`.
- Gemma 4: base `http://171.226.10.121:8000/llm/v1/`, key in `demo/config/app.local.properties` (not in git), model `gemma-4`
  (đã thử: chat 0,3 s, ảnh qua `image_url` data URI 0,7 s, tool calling OK). Cấu hình trong `demo/config/app.properties`.
- Câu demo (DEMO_QUERIES trong model.py): "tranh phong cảnh tông xanh", "tranh của Monet dưới 2 triệu",
  "tìm tranh giống ảnh này", "tìm đơn 20261001 của tôi", "đơn mới nhất của tôi đang ở đâu?".

## Báo cáo
Tiểu luận 5 chương theo bảng của thầy (Chapter 1 Requirement Determination, 2 Analysis, 3 AI in e-commerce,
4 Design, 5 Code), mỗi chương ~15 trang; định dạng trang trọng như `chapter4/design_04.tex`; Chương 4 theo dàn ý
4.1–4.6 trên bảng (có "Copy screen of DB" và "Present code + structure Packages/Classes").
Tên file theo bảng: `tieuluan_V<phiên bản>_04_10_<TÊNSV>_<3 số cuối mã SV>.pdf`, hiện là `tieuluan_V3_04_10_VUHUNGANH_022.pdf`. Đây là bài cá nhân (từ 11/11/2026); tên, mã sinh viên và phiên bản để trong `report/author.tex`.
