# Họa. web API

The JSON API of the demo shop, served by `WebServer` (package `com.ptit.ecom.presentation.web`) on
**http://127.0.0.1:8686** (`server.port` in `config/app.properties`). Every route calls one controller
operation of the design model (`tools/model.py`), shown in the last column of the index.
All examples below are **real responses** recorded from the running server (Gemma 4 online, Whisper online),
shortened where a list is long (`// … more`) or where an object repeats (`"…"`).

## 1. Conventions

| Topic | Rule |
|---|---|
| Format | Request and response bodies are JSON (UTF-8), except `POST /api/voice/transcribe` (raw audio body). |
| Money | US dollars as JSON numbers in plain decimal form: `89`, `119.6` (no trailing zeros). |
| Dates | Local time, ISO-8601: `LocalDateTime` → `"2026-10-29T17:12:57"`, `LocalDate` → `"2026-10-28"`. |
| Missing values | A `null` field is **left out** of the JSON (e.g. a frame has no `imageUrl`, an order not yet delivered has no `shipping.deliveredDate`). Test with `if (x.field)`, not `=== null`. |
| Images sent by the browser | Data URL string `data:image/jpeg;base64,…` (or `image/png`, `image/webp`), at most **5 MB**; the type is checked on the bytes (magic number), not on the name (NFR03). |
| Audio sent by the browser | Raw bytes of the recording (`audio/webm` from Chrome `MediaRecorder`, `audio/mp4` from Safari, WAV/AIFF), at most 10 MB. |
| Who is calling | Taken from the `hoa_session` cookie, **never** from the body: no route accepts a `customerId` except `/api/login` (NFR01). |

## 2. Session and login flow

Demo accounts (seed data, `db/seed.sql`):

| Account | Who | Data |
|---|---|---|
| `C001` | Nguyen Minh An, VIP level 2 (10 % discount, 1200 points) | addresses `A001`, `A002`; cart with P03; orders `20261001` (SHIPPED), `20261002` (DELIVERED) |
| `C002` | Tran Thu Binh, new customer (voucher WELCOME10) | address `A003`; empty cart; order `20261003` (PLACED, cash) |
| `ADMIN` | Administrator (UC12, UC13) | no cart, no orders; may call `/api/admin/**` only |

1. On page load call `GET /api/session`. Without a cookie it answers `{"admin": false}`.
2. If there is no `customerId`, sign in the default demo customer: `POST /api/login` with `{"customerId": "C001"}`.
   The response sets the cookie

       Set-Cookie: hoa_session=e4182935-64bc-45ab-ae1f-cbea482271ad; Path=/; HttpOnly; SameSite=Lax

   The cookie is `HttpOnly` (JavaScript cannot read it); a same-origin `fetch` sends it automatically.
3. The account switcher simply calls `POST /api/login` again with `C001`, `C002` or `ADMIN`; the new cookie replaces
   the old one. There is no logout route. Sessions live in memory, so after a server restart sign in again.
4. Access levels:
   * **public** — catalogue, search (text, voice, image, multimodal) and room routes;
   * **customer** — cart, checkout, orders and assistant: need a `C001`/`C002` session, otherwise
     `403 {"error": "Please sign in as a customer"}` (also for `ADMIN`);
   * **admin** — `/api/admin/**`: need the `ADMIN` session, otherwise `403 {"error": "Administrator only"}`.

## 3. Errors

Every error is a non-2xx status with one JSON field:

```json
{"error": "Order 20261003 was not found in your account"}
```

| Status | Meaning | Examples (real messages) |
|---|---|---|
| 400 | Invalid input | `Missing field quantity` · `Please upload a JPEG, PNG or WebP image` · `Only 7 left of The Starry Night` · `Unknown demo account` · `The request body is not valid JSON` · `Please enter the last four digits of the card` |
| 403 | Not signed in / wrong role | `Please sign in as a customer` · `Administrator only` |
| 404 | Unknown route, or an order that is **not found or not yours** (same message on purpose, NFR01) | `Order 20261003 was not found in your account` · `Unknown endpoint GET /api/nothing-here` |
| 409 | The request conflicts with the current state | `Your cart is empty` · `Only placed or processing orders can be cancelled` · `Cannot move order 20261003 from PROCESSING to DELIVERED` · `Out of stock: …` |
| 500 | Unexpected server error | `Unexpected error: …` |
| 503 | A service the request needs is down (only the Whisper server: `POST /api/voice/transcribe`) | `Voice search is unavailable right now. Please type your request.` |

AI fallbacks are **not** errors (NFR02): when Gemma 4 is unreachable the search, image, room and assistant routes
still answer `200` (see §6). The Whisper server is the one exception: when it is down,
`POST /api/voice/transcribe` answers `503`, and when it hears nothing it answers `200` with an empty `transcript`.

## 4. Endpoint index

| Method | Path | Access | Body / query | Returns | Controller operation (model) |
|---|---|---|---|---|---|
| POST | `/api/login` | public | `{customerId}` | `{customerId}` + cookie | `SessionManager.login` |
| GET | `/api/session` | public | — | session info | `SessionManager.customerOf`, `isAdmin` |
| GET | `/api/products` | public | — | `SearchResult[]` (whole catalogue) | `SearchController.search("")` |
| GET | `/api/search` | public | `?q=text` | `SearchResult[]` (≤ 12) | `SearchController.search(text)` |
| POST | `/api/voice/transcribe` | public | raw audio | `{transcript}` (`""` + `error` if nothing heard; 503 if Whisper is down) | `SearchController.transcribe(audioInput)` |
| POST | `/api/search/voice` | public | `{transcript}` | `SearchResult[]` (≤ 12) | `SearchController.searchVoice(transcript)` |
| POST | `/api/search/image` | public | `{image}` | `SearchResult[]` (≤ 12) | `SearchController.searchImage(image)` |
| POST | `/api/search/multimodal` | public | `{text, image}` | `SearchResult[]` (≤ 12) | `SearchController.searchMultimodal(text, image)` |
| POST | `/api/room/describe` | public | `{image}` | room reading (map) | `SearchController.describeRoom(image)` |
| POST | `/api/room/search` | public | `{image}` | `SearchResult[]` (3–5 picks; ≤ 8 without Gemma) | `SearchController.searchRoom(image)` |
| POST | `/api/assistant` | customer | `{message}` | `AssistantReply` | `AssistantController.ask(customerId, message)` |
| GET | `/api/cart` | customer | — | `Cart` | `CartController.viewCart(customerId)` |
| POST | `/api/cart/items` | customer | `{productId, quantity}` | `Cart` | `CartController.addItem(customerId, productId, quantity)` |
| PUT | `/api/cart/items` | customer | `{productId, quantity}` | `Cart` | `CartController.updateQuantity(customerId, productId, quantity)` |
| DELETE | `/api/cart/items` | customer | `?productId=P05` | `Cart` | `CartController.removeItem(customerId, productId)` |
| POST | `/api/addresses` | customer | `{houseNumber, street, district, city}` | new `Address` (with its `addressId`) | `CheckoutController.addAddress(customerId, houseNumber, street, district, city)` |
| POST | `/api/checkout` | customer | `{addressId, paymentMethod}` | new `Order` | `CheckoutController.checkout(customerId, cartId, addressId, paymentMethod)` |
| GET | `/api/orders` | customer | — | `Order[]` (newest first) | `OrderController.listOrders(customerId)` |
| GET | `/api/orders/{orderId}` | customer | — | `Order` | `OrderController.viewOrder(customerId, orderId)` |
| POST | `/api/orders/{orderId}/cancel` | customer | — | `Order` (CANCELLED) | `OrderController.cancelOrder(customerId, orderId)` |
| GET | `/api/admin/products` | admin | — | `Product[]` | `AdminController.listProducts()` |
| PUT | `/api/admin/products/{productId}` | admin | `{price, stockQuantity}` | `Product` | `AdminController.updateProduct(productId, price, stockQuantity)` |
| POST | `/api/admin/paintings` | admin | painting fields | new `Painting` | `AdminController.addPainting(painting)` |
| GET | `/api/admin/orders` | admin | — | `Order[]` of all customers | `AdminController.listAllOrders()` |
| PUT | `/api/admin/orders/{orderId}` | admin | `{status}` | `Order` | `AdminController.updateOrderStatus(orderId, status)` |

Static files (no `/api` prefix) are served from `web/`; an unknown path returns `web/index.html` (single-page app).
Files the backend provides for the UI: `/img/P01.jpg` … `/img/P32.jpg` (paintings), `/img/rooms/room1.jpg` …
`room3.jpg` with `/img/rooms/rooms.json` (sample rooms, their wall box and licence), and `/img/credits.json`
(credit, licence and Commons page of each painting image). Frames have no photo: draw them with CSS.
There is no single-product route: `GET /api/products` returns the whole catalogue (37 products) and the product
page picks one by `productId`.

## 5. JSON shapes

### Product (`Painting` or `Frame`)
`category` tells the subclass (`"PAINTING"` or `"FRAME"`); fields are those of the model classes
`Product`, `Painting`, `Artist` and `Frame`.

```json
{
  "style": "Impressionism",
  "subject": "seascape",
  "dominantColor": "blue",
  "medium": "Fine art paper",
  "yearCreated": 1872,
  "widthCm": 60,
  "heightCm": 46,
  "artist": {
    "artistId": "A01",
    "name": "Claude Monet",
    "nationality": "French",
    "lifeYears": "1840–1926"
  },
  "productId": "P01",
  "name": "Impression, Sunrise",
  "price": 79,
  "stockQuantity": 6,
  "imageUrl": "/img/P01.jpg",
  "description": "Museum-quality fine art paper of the 1872 original by Claude Monet.",
  "category": "PAINTING"
}
```

```json
{
  "material": "oak",
  "color": "brown",
  "sizeLabel": "40 x 60 cm",
  "productId": "F01",
  "name": "Natural oak frame 40 x 60",
  "price": 45,
  "stockQuantity": 20,
  "description": "Natural oak frame 40 x 60 in oak, anti-glare glass and hanging kit included.",
  "category": "FRAME"
}
```

### SearchResult
`score = α·textScore + β·imageScore + γ·businessScore` with α = 0.45, β = 0.45, γ = 0.10 (`ranking.*` in
`config/app.properties`; slide A06). All scores are in [0, 1]; results are sorted by `score`, highest first.
`reason` explains the match: its first part is the **source** — `Gemma 4` or `Keyword rules` (text and voice),
`Gemma 4 vision` or `Local colour reading` (image, room, multimodal) — followed by the matched attributes, the price
limit and the visual match, joined by ` ▪ `. When browsing (`/api/products`, or `/api/search?q=`) `reason` is `""`.

```json
{
  "product": {
    "style": "Impressionism",
    "subject": "seascape",
    "dominantColor": "blue",
    "medium": "Fine art paper",
    "yearCreated": 1872,
    "widthCm": 60,
    "heightCm": 46,
    "artist": {
      "artistId": "A01",
      "name": "Claude Monet",
      "nationality": "French",
      "lifeYears": "1840–1926"
    },
    "productId": "P01",
    "name": "Impression, Sunrise",
    "price": 79,
    "stockQuantity": 6,
    "imageUrl": "/img/P01.jpg",
    "description": "Museum-quality fine art paper of the 1872 original by Claude Monet.",
    "category": "PAINTING"
  },
  "textScore": 1.0,
  "imageScore": 0.0,
  "businessScore": 1.0,
  "score": 0.55,
  "reason": "Gemma 4 ▪ Impressionism ▪ Claude Monet ▪ under $100"
}
```

### Cart (`Cart`, `CartItem`, `Customer`, `Address`)
`cartPrice` is the price when the item was added; checkout re-reads the current price. `owner` is a `CustomerVIP`
(`vipLevel`, `discountRate`, `rewardPoints`) or a `CustomerNew` (`registeredDate`, `welcomeVoucher`).

```json
{
  "cartId": "CART-C001",
  "createdDate": "2026-10-28T08:00:00",
  "updatedDate": "2026-10-30T16:08:15",
  "owner": {
    "vipLevel": 2,
    "discountRate": 0.1,
    "rewardPoints": 1200,
    "customerId": "C001",
    "email": "an.nguyen@example.com",
    "phone": "+84 912 345 678",
    "dateOfBirth": "1998-04-12",
    "fullName": {
      "firstName": "An",
      "middleName": "Minh",
      "lastName": "Nguyen"
    },
    "addresses": [
      {
        "addressId": "A001",
        "houseNumber": "12",
        "street": "Trang Tien Street",
        "district": "Hoan Kiem",
        "city": "Hanoi"
      },
      {
        "addressId": "A002",
        "houseNumber": "45",
        "street": "Nguyen Chi Thanh Street",
        "district": "Dong Da",
        "city": "Hanoi"
      }
    ]
  },
  "items": [
    {
      "quantity": 1,
      "cartPrice": 89,
      "product": {
        "style": "Impressionism",
        "subject": "landscape",
        "dominantColor": "blue",
        "medium": "Canvas print",
        "yearCreated": 1875,
        "widthCm": 50,
        "heightCm": 61,
        "artist": {
          "artistId": "A01",
          "name": "Claude Monet",
          "nationality": "French",
          "lifeYears": "1840–1926"
        },
        "productId": "P03",
        "name": "Woman with a Parasol",
        "price": 89,
        "stockQuantity": 5,
        "imageUrl": "/img/P03.jpg",
        "description": "Museum-quality canvas print of the 1875 original by Claude Monet.",
        "category": "PAINTING"
      }
    },
    {
      "quantity": 2,
      "cartPrice": 129,
      "product": {
        "style": "Post-Impressionism",
        "subject": "landscape",
        "dominantColor": "blue",
        "medium": "Canvas print",
        "yearCreated": 1889,
        "widthCm": 92,
        "heightCm": 74,
        "artist": {
          "artistId": "A02",
          "name": "Vincent van Gogh",
          "nationality": "Dutch",
          "lifeYears": "1853–1890"
        },
        "productId": "P05",
        "name": "The Starry Night",
        "price": 129,
        "stockQuantity": 7,
        "imageUrl": "/img/P05.jpg",
        "description": "Museum-quality canvas print of the 1889 original by Vincent van Gogh.",
        "category": "PAINTING"
      }
    }
  ]
}
```

### Order (`Order`, `OrderItem`, `Shipping`, `Payment`)
`status`: `PLACED` → `PROCESSING` → `SHIPPED` → `DELIVERED`, or `CANCELLED`.
`shipping.status`: `PREPARING`, `IN_TRANSIT`, `DELIVERED`. `payments[].status`: `PENDING`, `SUCCEEDED`, `FAILED`.
A card payment (`PayCredit`) has `cardHolder`, `bankName`, `cardLast4`, `authorizationCode`; a cash payment
(`PayCash`) has `cashReceived`/`changeAmount` once collected. `totalAmount` = items × (1 − discount) + shipping fee
(8 USD). Example (customer and products shortened):

```json
{
  "orderId": "20261001",
  "orderDate": "2026-10-20T09:30:00",
  "status": "SHIPPED",
  "totalAmount": 107,
  "customer": {
    "customerId": "C001",
    "fullName": {
      "firstName": "An",
      "middleName": "Minh",
      "lastName": "Nguyen"
    },
    "…": "same Customer object as Cart.owner"
  },
  "items": [
    {
      "quantity": 1,
      "unitPrice": 35,
      "product": {
        "productId": "F03",
        "name": "Matte black aluminium frame 40 x 60",
        "price": 35,
        "category": "FRAME",
        "…": "full Product object"
      }
    },
    {
      "quantity": 1,
      "unitPrice": 75,
      "product": {
        "productId": "P10",
        "name": "The Great Wave off Kanagawa",
        "price": 75,
        "category": "PAINTING",
        "…": "full Product object"
      }
    }
  ],
  "shipping": {
    "shippingId": "SH-20261001",
    "carrier": "GHN Express",
    "trackingNumber": "GHN26102001",
    "shippingFee": 8,
    "status": "IN_TRANSIT",
    "address": {
      "addressId": "A001",
      "houseNumber": "12",
      "street": "Trang Tien Street",
      "district": "Hoan Kiem",
      "city": "Hanoi"
    }
  },
  "payments": [
    {
      "cardHolder": "NGUYEN MINH AN",
      "bankName": "Vietcombank",
      "cardLast4": "4242",
      "authorizationCode": "AUTH-7731",
      "paymentId": "PAY-20261001",
      "amount": 107,
      "paymentDate": "2026-10-20T09:30:00",
      "status": "SUCCEEDED"
    }
  ]
}
```

## 6. Endpoints

### POST /api/login · GET /api/session
Request `{"customerId": "C001"}` (or `"C002"`, `"ADMIN"`) → `200 {"customerId": "C001"}` + `Set-Cookie`.
Unknown account → `400 Unknown demo account`.

`GET /api/session` — customer (`cartCount` = number of lines in the cart):

```json
{
  "customerId": "C001",
  "admin": false,
  "name": "Nguyen Minh An",
  "discountRate": 0.1,
  "addresses": [
    {
      "addressId": "A001",
      "houseNumber": "12",
      "street": "Trang Tien Street",
      "district": "Hoan Kiem",
      "city": "Hanoi"
    },
    {
      "addressId": "A002",
      "houseNumber": "45",
      "street": "Nguyen Chi Thanh Street",
      "district": "Dong Da",
      "city": "Hanoi"
    }
  ],
  "cartCount": 1
}
```

Administrator: `{"customerId": "ADMIN", "admin": true}` · nobody signed in: `{"admin": false}`

### GET /api/products
The whole catalogue as `SearchResult[]`: 32 paintings first, then 5 frames, ranked by `businessScore`
(sold-out items last), `reason` empty.

### GET /api/search?q=…
Text search (UC01, slide A06 `search_text`). Gemma 4 turns the text into a `CommonQuery`
(style, subject, colour, artist, maxPrice); keyword rules take over when Gemma is offline.
`maxPrice` is a hard filter. At most 12 results. Example `GET /api/search?q=Monet%20paintings%20under%20100%20dollars`:

```jsonc
[
  {
    "product": {
      "style": "Impressionism",
      "subject": "seascape",
      "dominantColor": "blue",
      "medium": "Fine art paper",
      "yearCreated": 1872,
      "widthCm": 60,
      "heightCm": 46,
      "artist": {
        "artistId": "A01",
        "name": "Claude Monet",
        "nationality": "French",
        "lifeYears": "1840–1926"
      },
      "productId": "P01",
      "name": "Impression, Sunrise",
      "price": 79,
      "stockQuantity": 6,
      "imageUrl": "/img/P01.jpg",
      "description": "Museum-quality fine art paper of the 1872 original by Claude Monet.",
      "category": "PAINTING"
    },
    "textScore": 1.0,
    "imageScore": 0.0,
    "businessScore": 1.0,
    "score": 0.55,
    "reason": "Gemma 4 ▪ Impressionism ▪ Claude Monet ▪ under $100"
  },
  {
    "product": {
      "style": "Impressionism",
      "subject": "flowers",
      "dominantColor": "green",
      "medium": "Canvas print",
      "yearCreated": 1906,
      "widthCm": 60,
      "heightCm": 56,
      "artist": {
        "artistId": "A01",
        "name": "Claude Monet",
        "nationality": "French",
        "lifeYears": "1840–1926"
      },
      "productId": "P02",
      "name": "Water Lilies",
      "price": 69,
      "stockQuantity": 8,
      "imageUrl": "/img/P02.jpg",
      "description": "Museum-quality canvas print of the 1906 original by Claude Monet.",
      "category": "PAINTING"
    },
    "textScore": 1.0,
    "imageScore": 0.0,
    "businessScore": 1.0,
    "score": 0.55,
    "reason": "Gemma 4 ▪ Impressionism ▪ Claude Monet ▪ under $100"
  }
  // … 4 more results, 6 in total
]
```

`blue landscape paintings` → P03 (Gemma 4 ▪ landscape ▪ blue), P05 (Gemma 4 ▪ landscape ▪ blue), P21 (Gemma 4 ▪ landscape ▪ blue), …

### POST /api/voice/transcribe
Body: the raw recording (any `Content-Type`). The Java server forwards it to the self-hosted Whisper server
(`WhisperClient`, always `language=en`); the audio is not stored. Show the transcript in an editable field, then
call `POST /api/search/voice`. Three possible answers:

| Case | Status | Body |
|---|---|---|
| Words heard (0.79 s for `voice-server/samples/en/e01.webm`) | 200 | `{"transcript": "blue landscape paintings"}` |
| Nothing heard (silence, noise) | 200 | `{"transcript": "", "error": "We couldn't hear you. Please try again or type your request."}` |
| Whisper server not reachable | 503 | `{"error": "Voice search is unavailable right now. Please type your request."}` |

The UI shows "We couldn't hear you" when `transcript` is empty and the 503 message when voice search is down;
in both cases the customer can type instead.

### POST /api/search/voice
Request `{"transcript": "blue landscape paintings"}` → `SearchResult[]`, same ranking as text search
(`CommonQuery.type = "voice"`).

### POST /api/search/image
"Show me paintings similar to this image" (UC03). Request `{"image": "data:image/jpeg;base64,…"}`.
Gemma 4 vision reads style, subject, colour and artist; the reading becomes a vector compared by cosine similarity
(`VectorIndex`). Example with a different photo of Van Gogh's *Sunflowers* (`data/eval_images/Q01.jpg`):

```jsonc
[
  {
    "product": {
      "style": "Post-Impressionism",
      "subject": "flowers",
      "dominantColor": "yellow",
      "medium": "Canvas print",
      "yearCreated": 1888,
      "widthCm": 56,
      "heightCm": 72,
      "artist": {
        "artistId": "A02",
        "name": "Vincent van Gogh",
        "nationality": "Dutch",
        "lifeYears": "1853–1890"
      },
      "productId": "P06",
      "name": "Sunflowers",
      "price": 119,
      "stockQuantity": 6,
      "imageUrl": "/img/P06.jpg",
      "description": "Museum-quality canvas print of the 1888 original by Vincent van Gogh.",
      "category": "PAINTING"
    },
    "textScore": 1.0,
    "imageScore": 1.0000000000000002,
    "businessScore": 1.0,
    "score": 1.0000000000000002,
    "reason": "Gemma 4 vision ▪ Post-Impressionism ▪ flowers ▪ yellow ▪ Vincent van Gogh ▪ 100% visual match"
  },
  {
    "product": {
      "style": "Post-Impressionism",
      "subject": "cityscape",
      "dominantColor": "yellow",
      "medium": "Canvas print",
      "yearCreated": 1888,
      "widthCm": 52,
      "heightCm": 66,
      "artist": {
        "artistId": "A02",
        "name": "Vincent van Gogh",
        "nationality": "Dutch",
        "lifeYears": "1853–1890"
      },
      "productId": "P07",
      "name": "Café Terrace at Night",
      "price": 109,
      "stockQuantity": 5,
      "imageUrl": "/img/P07.jpg",
      "description": "Museum-quality canvas print of the 1888 original by Vincent van Gogh.",
      "category": "PAINTING"
    },
    "textScore": 0.75,
    "imageScore": 0.6666666666666667,
    "businessScore": 1.0,
    "score": 0.7375,
    "reason": "Gemma 4 vision ▪ Post-Impressionism ▪ yellow ▪ Vincent van Gogh ▪ 67% visual match"
  }
  // … 10 more results, 12 in total
]
```

### POST /api/search/multimodal
Request `{"text": "under 150 dollars", "image": "data:image/jpeg;base64,…"}` → `SearchResult[]` combining the text
(`textScore`, price filter) and the image (`imageScore`). Top result with a photo of *The Great Wave*:
`P10 The Great Wave off Kanagawa` — `Gemma 4 vision ▪ under $150 ▪ 100% visual match`.

### POST /api/room/describe
"Try it in your room" step 2 (UC14). Request `{"image": "data:image/jpeg;base64,…"}` (a room photo; it is kept in
memory only, never stored). Response: a flat map of **strings**; lists are comma-separated.

```json
{
  "room": "Living room",
  "palette": "#d1d5db,#4b5563,#facc15,#ffffff",
  "colors": "grey,yellow,white",
  "tone": "neutral",
  "interior": "Modern Minimalist",
  "mood": "Serene, Sophisticated",
  "light": "bright",
  "style": "Impressionism",
  "subject": "cityscape",
  "color": "blue",
  "reading": "A soft impressionist cityscape would complement the cool grey tones and the structured elegance of the sofa.",
  "wall_box": "0.39,0.22,0.23,0.23",
  "ai": "gemma"
}
```

| Key | Meaning |
|---|---|
| `room`, `interior`, `mood` | free text from Gemma (e.g. tags `LIVING ROOM ▪ MODERN MINIMALIST ▪ SERENE`) |
| `palette` | comma-separated hex colours of the room |
| `colors` | comma-separated colour names |
| `tone` / `light` | `warm`, `cool`, `neutral` / `bright`, `soft`, `dim` |
| `style`, `subject`, `color` | the painting Gemma suggests, in the catalogue vocabulary (§7) |
| `reading` | one sentence to display |
| `wall_box` | optional `"x,y,w,h"` as fractions 0..1 of the photo: free wall area. Often imprecise: use it only if plausible, otherwise default to the upper-centre third. The sample rooms carry a curated `wallBox` in `/img/rooms/rooms.json`. |
| `ai` | `gemma`, or `local` when Gemma is offline |

Gemma offline (`ai = local`): only the average colour is read on the server —
`{"ai": "local", "color": "pink", "colors": "pink", "palette": "#b2aaa5", "reading": "Gemma 4 is not reachable, so only the main colour was read on this computer."}`

### POST /api/room/search
"Try it in your room" step 3. Same request as `/api/room/describe`; three steps inside `SearchService.searchRoom`:

1. the room reading of `/api/room/describe` (cached per photo, so calling describe first costs no extra Gemma call);
2. a shortlist of the 12 paintings closest to the suggested style, subject and colour (`VectorIndex`, cosine);
3. Gemma 4 sees the photo again with the shortlist (`productId | title | artist | style | subject | colour | medium |
   size | USD price`) and picks the **3–5 paintings that fit best, in its order of preference**, each with **one
   English sentence (15–25 words)** that names concrete things of the room (wall or sofa colours, light, style, mood)
   and of the painting. Ids outside the shortlist are ignored; an empty, too short or generic sentence is replaced by
   one built from the attributes.

Without Gemma: the vector ranking (up to 8 paintings; best sellers fill up when fewer than 3 match), each with a full
sentence built from the painting's attributes and what is known of the room. In this route `reason` is that sentence
(no ` ▪ ` source prefix): take the AI badge from the `ai` field of `/api/room/describe`. The scores are kept for a
debug overlay, but the order is Gemma's, not the score. Real response for sample room 1 (1.39 s
after describe; products shortened):

```json
[
  {
    "product": {
      "productId": "P01",
      "name": "Impression, Sunrise",
      "price": 79,
      "category": "PAINTING",
      "…": "full Product object"
    },
    "textScore": 0.667,
    "imageScore": 0.667,
    "businessScore": 1.0,
    "score": 0.7,
    "reason": "The soft blue tones of this seascape beautifully complement your light grey sofa and the bright, airy atmosphere of the room."
  },
  {
    "product": {
      "productId": "P03",
      "name": "Woman with a Parasol",
      "price": 89,
      "category": "PAINTING",
      "…": "full Product object"
    },
    "textScore": 0.667,
    "imageScore": 0.667,
    "businessScore": 1.0,
    "score": 0.7,
    "reason": "This blue impressionist landscape enhances the serene mood of your living space while matching the cool tones of your furniture."
  },
  {
    "product": {
      "productId": "P12",
      "name": "Sudden Shower over Shin-Ōhashi Bridge",
      "price": 59,
      "category": "PAINTING",
      "…": "full Product object"
    },
    "textScore": 0.667,
    "imageScore": 0.667,
    "businessScore": 1.0,
    "score": 0.7,
    "reason": "The blue hues in this cityscape create a sophisticated connection with your grey sofa and the minimalist, modern interior style."
  },
  {
    "product": {
      "productId": "P17",
      "name": "Bal du moulin de la Galette",
      "price": 139,
      "category": "PAINTING",
      "…": "full Product object"
    },
    "textScore": 0.667,
    "imageScore": 0.667,
    "businessScore": 0.8,
    "score": 0.68,
    "reason": "Its gentle blue palette and impressionist style add a touch of elegance to your bright room and neutral grey seating."
  },
  {
    "product": {
      "productId": "P21",
      "name": "Wanderer above the Sea of Fog",
      "price": 109,
      "category": "PAINTING",
      "…": "full Product object"
    },
    "textScore": 0.333,
    "imageScore": 0.333,
    "businessScore": 1.0,
    "score": 0.4,
    "reason": "The deep blue colors of this landscape work perfectly with your grey sofa to create a calm and contemplative mood."
  }
]
```

Gemma offline (first result): `"Its pink tones and impressionist portrait work with the pink colour read from your photo, and keep the wall calm and simple."`

### POST /api/assistant
Customer only. Request `{"message": "find my order 20261001"}`. Gemma 4 chooses one of four tools
(`search_paintings`, `find_order`, `latest_order`, `list_orders`); the customer id comes from the session, never
from the model.

```json
{
  "answer": "Your order 20261001 has been shipped and is currently in transit via GHN Express. It includes \"The Great Wave off Kanagawa\" with a matte black aluminium frame. Your tracking number is GHN26102001.",
  "toolsUsed": [
    "find_order"
  ],
  "aiUsed": true
}
```

```json
{
  "answer": "Your latest order (#20261001) has been shipped and is currently in transit via GHN Express. You can track your package using the tracking number GHN26102001.",
  "toolsUsed": [
    "latest_order"
  ],
  "aiUsed": true
}
```

Gemma offline: rule-based answer, prefixed and flagged —
`{"answer": "(Gemma 4 is offline) Order 20261001 is shipped, total $107, tracking GHN Express GHN26102001.", "toolsUsed": ["find_order"], "aiUsed": false}`

### Cart routes
`GET /api/cart` → `Cart` (the customer's cart is created on first use).
`POST /api/cart/items` `{"productId": "P05", "quantity": 1}` adds (or increases) a line; `400` if the product does not
exist or the stock is too low. `PUT /api/cart/items` `{"productId": "P05", "quantity": 2}` sets the quantity
(`0` removes the line). `DELETE /api/cart/items?productId=P05` removes it. All four return the whole `Cart`
(example in §5). To buy a painting with a frame (product page, room preview), add both products.

### POST /api/addresses
A delivery address typed at checkout (UC07). Request `{"houseNumber": "7B", "street": "Lang Ha Street", "district": "Ba Dinh", "city": "Hanoi"}`;
all four parts are required. The server trims them, collapses repeated blanks, stores the address for the signed-in
customer (`CheckoutController.addAddress` → `CheckoutService.addAddress` → `CustomerRepository.saveAddress`) and
answers with the new address. The page then selects it, and `POST /api/checkout` uses its `addressId`.

```json
{"addressId": "A004", "houseNumber": "7B", "street": "Lang Ha Street", "district": "Ba Dinh", "city": "Hanoi"}
```

Errors: `400 Street is required` (any part empty), `400 House number must be at most 20 characters` (limits: house
number 20, street 100, district 60, city 60, as in the `address` table), `400 Missing field street`,
`403 Please sign in as a customer`.

### POST /api/checkout
Request `{"addressId": "A001", "paymentMethod": "CARD:4242:Nguyen Minh An"}`; `paymentMethod` is `"CASH"` (paid on
delivery, payment `PENDING`) or `"CARD:<last 4 digits>:<card holder>"` (authorisation simulated, payment `SUCCEEDED`).
The server checks the cart owner, re-reads prices and stock, applies the VIP discount, adds the 8 USD shipping
fee, saves the order, decreases stock and empties the cart (slide A05). Response: the new order.

```json
{
  "orderId": "26103016081553",
  "orderDate": "2026-10-30T16:08:15",
  "status": "PLACED",
  "totalAmount": 119.6,
  "customer": {
    "customerId": "C001",
    "fullName": {
      "firstName": "An",
      "middleName": "Minh",
      "lastName": "Nguyen"
    },
    "…": "same Customer object as Cart.owner"
  },
  "items": [
    {
      "quantity": 1,
      "unitPrice": 35,
      "product": {
        "productId": "F03",
        "name": "Matte black aluminium frame 40 x 60",
        "price": 35,
        "category": "FRAME",
        "…": "full Product object"
      }
    },
    {
      "quantity": 1,
      "unitPrice": 89,
      "product": {
        "productId": "P03",
        "name": "Woman with a Parasol",
        "price": 89,
        "category": "PAINTING",
        "…": "full Product object"
      }
    }
  ],
  "shipping": {
    "shippingId": "SH-26103016081553",
    "carrier": "GHN Express",
    "shippingFee": 8,
    "status": "PREPARING",
    "address": {
      "addressId": "A001",
      "houseNumber": "12",
      "street": "Trang Tien Street",
      "district": "Hoan Kiem",
      "city": "Hanoi"
    }
  },
  "payments": [
    {
      "cardHolder": "Nguyen Minh An",
      "bankName": "Demo card",
      "cardLast4": "4242",
      "authorizationCode": "SIM-741DE072",
      "paymentId": "PAY-26103016081553",
      "amount": 119.6,
      "paymentDate": "2026-10-30T16:08:15",
      "status": "SUCCEEDED"
    }
  ]
}
```

Errors: `409 Your cart is empty`, `409 Out of stock: <name>`, `400 Address A9 does not belong to customer C001`,
`400 Please enter the last four digits of the card`.

### Order routes
`GET /api/orders` → the customer's orders, newest first. `GET /api/orders/20261001` → one order (example in §5);
another customer's order → `404` with the same message as a missing one.
`POST /api/orders/{orderId}/cancel` (UC11) → the order with `"status": "CANCELLED"`; only `PLACED` or `PROCESSING`
orders, otherwise `409 Only placed or processing orders can be cancelled`.

### Admin routes (UC12, UC13)
`GET /api/admin/products` → `Product[]` (plain products, not `SearchResult`).

`PUT /api/admin/products/P05` `{"price": 129, "stockQuantity": 7}` → the updated product; negative values → `400`.

`POST /api/admin/paintings` — all fields required; `artistId` may be new (then `artistName` creates the artist);
`imageUrl` must be an image already in `web/img` (no upload); the new id is the next free `P` number.

```json
{
  "artistId": "A02",
  "artistName": "Vincent van Gogh",
  "name": "Almond Blossoms",
  "price": 99,
  "stockQuantity": 5,
  "style": "Post-Impressionism",
  "subject": "flowers",
  "dominantColor": "blue",
  "medium": "Canvas print",
  "yearCreated": 1890,
  "widthCm": 92,
  "heightCm": 73,
  "imageUrl": "/img/P06.jpg"
}
```

Response:

```json
{
  "style": "Post-Impressionism",
  "subject": "flowers",
  "dominantColor": "blue",
  "medium": "Canvas print",
  "yearCreated": 1890,
  "widthCm": 92,
  "heightCm": 73,
  "artist": {
    "artistId": "A02",
    "name": "Vincent van Gogh"
  },
  "productId": "P33",
  "name": "Almond Blossoms",
  "price": 99,
  "stockQuantity": 5,
  "imageUrl": "/img/P06.jpg",
  "description": "Museum-quality canvas print of the 1890 original by Vincent van Gogh.",
  "category": "PAINTING"
}
```

`GET /api/admin/orders` → every order of every customer, newest first (`Order[]`).

`PUT /api/admin/orders/20261003` `{"status": "PROCESSING"}` → the updated order. Only one step forward is allowed:
`PLACED → PROCESSING → SHIPPED → DELIVERED` (`Order.advanceTo`); `SHIPPED` also sets the shipping to `IN_TRANSIT`,
`DELIVERED` sets it to `DELIVERED` with `deliveredDate`. Other moves → `409`, e.g.
`Cannot move order 20261003 from PROCESSING to DELIVERED`; an unknown status name → `400`.

## 7. Vocabulary

| Field | Values |
|---|---|
| `Painting.style` | Impressionism, Post-Impressionism, Ukiyo-e, Art Nouveau, Baroque, Romanticism, Expressionism, Abstract, Realism, Naive art |
| `Painting.subject` | landscape, seascape, flowers, portrait, still life, cityscape, everyday life, abstract |
| `Painting.dominantColor`, `Frame.color` | blue, green, yellow, red, orange, brown, white, black, purple, pink |
| `Painting.medium` | Canvas print, Fine art paper |
| `Frame.material` | oak, walnut, aluminium, gilded wood, painted pine (F01–F05) |

These lists are the dimensions of the one-hot vectors in `VectorIndex` (style 10 + subject 8 + colour 10 = 28).
