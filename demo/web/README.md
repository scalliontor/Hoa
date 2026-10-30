# Họa. web shop: browser views

This folder holds the presentation layer of the demo. It is a single-page shop in plain HTML, CSS and JavaScript
(ES modules). There is no build step and no framework. The Java `WebServer` serves the files from this folder,
and every unknown path falls back to `index.html`. The views read and write data only through the JSON API
(`../API.md`). They never touch the database.

## Files and the model classes they implement

Each view is one object whose public methods have the same names as the view classes in `model.py`
(slide A06 presentation layer). Helpers that are not part of a model class are private to the file or are
marked "page helper (not part of the model class)".

| File | Model class | Public methods | Report section |
|---|---|---|---|
| `js/search-ui.js` | `SearchUI` | `submitText`, `submitVoice`, `submitImage`, `submitMultimodal` | 5.6 Multimodal Search, 5.9 User Interface |
| `js/voice-input.js` | `VoiceInput` | `start`, `stop`, `upload`, `onTranscript` | 5.7 Speech through the self-hosted Whisper server |
| `js/image-upload.js` | `ImageUpload` | `choose`, `validate`, `preview` | 5.6, 5.9 |
| `js/search-result-view.js` | `SearchResultView` | `render`, `renderEmpty` | 5.6 Retrieval and ranking, 5.9 |
| `js/cart-view.js` | `CartView` | `render`, `checkout` | 5.8 Checkout and Orders at Run Time |
| `js/order-view.js` | `OrderView` | `render`, `lookup` | 5.8 |
| `js/assistant-view.js` | `AssistantView` | `send`, `render` | 5.7 The curator assistant |
| `js/admin-view.js` | `AdminView` | `renderProducts`, `saveProduct`, `renderOrders`, `updateStatus` | 5.8, 5.9 (UC12, UC13) |
| `js/room-preview.js` | `RoomPreview` | `chooseRoom`, `placePainting`, `renderSuggestions` | 3 (UC14), 5.9 |
| `js/core.js` | (shared helpers) | `api`, session, formatting, card templates, `toJpeg`, developer view | 5.5 Composition Root and Web Layer |
| `js/app.js` | (router and page layout) | hash routes, header, drawer, photo drop and paste | 5.9 |
| `css/base.css` | (design system) | colour tokens (dark and light), type, buttons, cards, forms, header, footer | 5.9 |
| `css/screens.css` | (screen styles) | home, collection, painting, room, cart, orders, assistant, admin | 5.9 |
| `css/fonts.css`, `fonts/` | (bundled fonts) | Inter Tight and JetBrains Mono, OFL 1.1 (`fonts/LICENSE.md`) | 5.1 Technology Stack |
| `index.html` | (page shell) | header, `<main id="app">`, footer, assistant drawer | 5.9 |

The model view `RoomPreview` drives the use case "Find a painting for my room" (UC14). `SearchController.describeRoom`
and `SearchController.searchRoom` sit behind `POST /api/room/describe` and `POST /api/room/search`.

## Screens and routes

| Route | Screen |
|---|---|
| `#/` | Home: hero, selected works, "Five easy ways to find it", room teaser |
| `#/collection?q=…` | Search by words, by voice (microphone, editable transcript), or with a photo. A room photo goes straight to `#/room`. "or find paintings similar to a photo" runs the image search (UC04). Results are shown as cards with a short reason. |
| `#/painting/P10` | Painting page: the print on a wall, frame choice, quantity, Add to cart, Try it in my room |
| `#/room?p=P10` | Try it in your room. The photo is read ("What we see"). The best pick is hung at its real size, with "Why it fits" under it. The other picks are in a strip. You can change the wall width, print size, frame, passe-partout and light, then use Save image and Add to cart. |
| `#/cart` | Cart lines, VIP discount, flat $8 delivery, address, cash or card (last four digits only) |
| `#/orders?lookup=…` | My orders with a status timeline, cancel before shipping, and look-up by id (other customers' orders are refused) |
| `#/admin?tab=orders` | Back office (staff account): price and stock, add a painting, move orders one step |

The account menu switches between the demo accounts Nguyen Minh An (VIP), Tran Thu Binh (new) and Gallery staff.
The customer id always comes from the server session.

## Privacy rules kept by the views

- A room photo or search photo is turned into a JPEG of at most 1600 px in the browser. EXIF data, such as the
  location, is dropped. The photo is sent to the server only to be read and is never stored there. The last room
  photo is kept in `sessionStorage` (this tab only), so a reload does not lose it.
- Checkout sends `CARD:<last4>:<holder>`. The full card number never leaves the browser.

## Developer view

Shoppers see no scores, model names or tool calls. To see them, add `?debug=1` to the address or press
Shift + D. The developer view shows the score breakdown S = αStext + βSimage + γSbusiness on every result card,
the AI mode (Gemma 4 or keyword fallback), the response time, the room reading behind the picks, and the tools
the assistant called. It is never saved in the browser: Shift + D lasts until the next reload, and `?debug=1` only
applies while it is in the address.
