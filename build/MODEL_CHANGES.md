# Model changes made by the DEMO agent

One row per change: date, the element of `tools/model.py` (DESIGN) and why. The VP, REPORT and SLIDES agents
read model.py again after each change. Rows marked "no signature change" only change behaviour behind an
existing signature; the diagrams stay valid.

| Date | Change | Reason |
|---|---|---|
| 2026-10-29 | `SearchResult` gains `-reason: String` | The UI shows why a product is suggested ("Gemma 4 ▪ landscape ▪ blue ▪ under $100") in every search mode; this supports the explanation of AI results in Chapter 3. |
| 2026-10-29 | `SearchService.describeRoom(image: byte[]): Map<String, String>` and `SearchController.describeRoom(image: byte[]): Map<String, String>` | The "Try it in your room" page (UC14) first shows Gemma's reading of the room (palette, style, mood, wall area); `searchRoom` returns only the paintings. `ImageService` remembers Gemma's answer per photo, so `describeRoom` followed by `searchRoom` reads the room once. |
| 2026-10-29 | No signature change: `SearchService.searchRoom(image)` now works in three steps — room reading, a shortlist of 12 paintings by cosine similarity, then Gemma 4 sees the photo again and picks the 3–5 best with one English sentence each (15–25 words) in `SearchResult.reason`. `ImageService.describe(image, purpose)` accepts a third purpose, `"pick:"` followed by the shortlist lines, and answers `productId -> reason`. | User request: an uploaded room photo should give paintings chosen for that room, each with a clear reason that names what is seen in the photo and the painting's own colours, subject or style. Ids outside the shortlist are ignored, short or generic sentences are replaced, and without Gemma the vector ranking stays with a sentence built from the attributes (NFR02). |
| 2026-10-29 | No signature change: "not found" errors (`OrderService.getOrder`, `updateStatus`, `ProductService.updatePriceAndStock`) are `NoSuchElementException` | `WebServer` answers them with HTTP 404, the same for an order that does not exist and an order of another customer (NFR01). |
| 2026-10-30 | No signature change: `SpeechService.transcribe(audioInput)` returns `""` when Whisper hears no words and `null` only when the Whisper server cannot be reached | `WebServer` can tell the two apart: `200 {"transcript": "", "error": "We couldn't hear you…"}` versus `503 {"error": "Voice search is unavailable right now…"}`. |
