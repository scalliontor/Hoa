// app.js — router and page layout of the Họa. single-page app. Each page builds its frame here and hands
// the data work to the model views (SearchUI, SearchResultView, CartView, OrderView, RoomPreview, AdminView…).
import {
  ACCOUNTS, addToCart, api, cap, developer, esc, framedHtml, frameLook, frames, loadCredits, loadProducts, login, money,
  onSession, paintings, productCard, refreshSession, setDeveloper, state, toast,
} from "./core.js";
import { SearchUI } from "./search-ui.js";
import { SearchResultView } from "./search-result-view.js";
import { VoiceInput } from "./voice-input.js";
import { ImageUpload } from "./image-upload.js";
import { CartView } from "./cart-view.js";
import { OrderView } from "./order-view.js";
import { AssistantView } from "./assistant-view.js";
import { AdminView } from "./admin-view.js";
import { RoomPreview, framePillsHtml, loadSampleRooms, restoreRoom, wireRoomControls } from "./room-preview.js";

const app = document.getElementById("app");
const QUICK_QUERIES = ["blue landscape paintings", "Monet paintings under 100 dollars", "calm Japanese prints with water",
  "yellow flowers for a kitchen", "portraits of women"];
const icons = {
  mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/></svg>',
  image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="5" width="18" height="14" rx="1"/><circle cx="9" cy="10" r="1.6"/><path d="M21 16l-5-5-8 8"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 15V4M7.5 8.5L12 4l4.5 4.5"/><path d="M4 15v4a1 1 0 001 1h14a1 1 0 001-1v-4"/></svg>',
  room: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.3"><rect x="6" y="6" width="36" height="36"/><rect x="17" y="12" width="14" height="11"/><path d="M6 34h36M12 34v-5h24v5"/></svg>',
};
const PASTE_KEY = /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘V" : "Ctrl+V";

// Where a photo dropped or pasted anywhere on the page goes; pages without a photo field open "Find for my room".
let photoTarget = null;
let pendingPhoto = null;

// ------------------------------------------------------------------ router

const routes = { "": home, collection, painting, room, cart, orders, admin };

async function route() {
  const [path, query = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const [name, id] = path.split("/");
  const params = new URLSearchParams(query);
  const page = routes[name] || home;
  document.querySelectorAll(".nav [data-route]").forEach((link) => link.classList.toggle("active", link.dataset.route === name));
  document.getElementById("header").classList.toggle("solid", name !== "");
  document.getElementById("header").classList.remove("menu-open");
  window.onresize = null;
  photoTarget = null;
  try {
    await page(params, id);
  } catch (error) {
    app.innerHTML = `<section class="page wrap"><div class="empty"><p class="h3">Something went wrong</p><p>${esc(error.message)}</p>
      <a class="btn" href="#/" style="margin-top:22px">Back to the home page</a></div></section>`;
  }
  window.scrollTo({ top: 0 });
}

// ------------------------------------------------------------------- pages

function home() {
  const works = paintings();
  const hero = state.byId.get("P05") || works[0];
  const featured = ["P10", "P14", "P01", "P21", "P06", "P32"].map((id) => state.byId.get(id)).filter(Boolean);
  const artists = [...new Set(works.map((p) => p.artist.name))];
  app.innerHTML = `
  <section class="hero">
    <div class="hero-media"><img src="${esc(hero.imageUrl)}" alt=""></div>
    <div class="hero-top mono" id="hero-line">Describe it ▪ Say it ▪ Show us your room</div>
    <div class="hero-content">
      <div>
        <h1 class="display">Paintings that<br>find you.</h1>
        <p class="lead">Museum-quality prints of ${works.length} masterpieces. Describe what you love, say it — or upload a photo of your room and our AI curator picks paintings that fit it.</p>
        <div class="row" style="margin-top:30px">
          <a class="btn solid" href="#/collection">Explore the collection</a>
          <a class="btn" href="#/room">Upload a photo of your room</a>
        </div>
      </div>
      <a class="hero-caption mono" href="#/painting/${esc(hero.productId)}">${esc(hero.artist.name)} ▪ ${esc(hero.name)} ▪ ${esc(hero.yearCreated)}</a>
    </div>
    <div class="scroll-hint mono">Scroll to explore ↓</div>
  </section>
  <div class="marquee"><div class="marquee-track">${[...artists, ...artists].map((a) => `<span>${esc(a)}</span>`).join("")}</div></div>
  <section class="wrap" style="padding:96px var(--gutter)">
    <div class="section-head">
      <div><span class="label">Selected works</span><h2 class="h2" style="margin-top:12px">Prints of the paintings<br>people stop for.</h2></div>
      <a class="btn" href="#/collection">See all ${works.length} works</a>
    </div>
    <div class="grid-2">${featured.map((p) => productCard(p)).join("")}</div>
  </section>
  <section class="wrap section">
    <div class="section-head">
      <div><span class="label">How it works</span><h2 class="h2" style="margin-top:12px">Five easy ways to find it.</h2></div>
      <p class="lead">No art vocabulary needed. Tell us, show us, or simply ask.</p>
    </div>
    <div class="ai-strip">
      ${aiItem("01", "Describe it", "Type what you have in mind — “Monet paintings under 100 dollars” — and we find the style, colours, artist and budget you mean.", "Try a search", "#/collection?q=Monet%20paintings%20under%20100%20dollars")}
      ${aiItem("02", "Say it", "Tap the microphone and just say it. You can fix the words before we search.", "Search by voice", "#/collection?voice=1")}
      ${aiItem("03", "Show us your room", "Upload a photo of your room — our AI curator picks paintings that fit it, and tells you why.", "Upload a photo", "#/collection?upload=1")}
      ${aiItem("04", "See it on your wall", "Hang any painting on your own wall at its real size, with the frame you like, before you buy.", "Try it on", "#/room")}
      ${aiItem("05", "Just ask", "“Where is my latest order?” or “a calm blue painting under 100 dollars” — our assistant is happy to help.", "Ask the assistant", "#/orders?assistant=1")}
    </div>
  </section>
  <section class="wrap section">
    <div class="teaser">
      <div class="teaser-media"><img src="/img/rooms/room1.jpg" alt="A bright living room">
        <div class="hung">${framedHtml(state.byId.get("P10") || hero, frames().find((f) => f.material === "aluminium"), { framePx: 6, matPx: 10 })}</div></div>
      <div class="stack" style="gap:20px">
        <span class="label">Find a painting for my room</span>
        <h2 class="h2">See it on your wall<br>before it ships.</h2>
        <p class="lead">Upload a photo of your room — our AI curator picks paintings that fit it, then hangs them at their real size with the frame of your choice.</p>
        <div class="row"><a class="btn solid" href="#/room">Try it in your room</a></div>
      </div>
    </div>
  </section>`;
  scramble(document.getElementById("hero-line"));
}

function aiItem(num, title, text, action, href) {
  return `<a class="ai-item" href="${href}"><span class="num">${num}</span><h3>${title}</h3><p>${text}</p><span class="tag">${action} ↗</span></a>`;
}

/** The photo drop zone used on the Collection page and on "Find for my room". */
function photoDropHtml(id, buttonId, extra = "") {
  return `<div class="image-drop" id="${id}" role="button" tabindex="0" aria-label="Upload a photo of your room">
    <span class="image-drop-icon">${icons.room}</span>
    <div class="image-drop-text">
      <strong>Upload a photo of your room</strong>
      <span>Our AI curator picks paintings that fit it. Drag &amp; drop a photo here, paste it (${PASTE_KEY}) or choose one.</span>
    </div>
    <div class="image-drop-actions">
      <button type="button" class="btn solid small" id="${buttonId}">${icons.upload}Upload photo</button>${extra}
    </div>
  </div>`;
}

/** Collection: the search bar (words, voice) and the room photo panel above the result grid. */
async function collection(params) {
  app.innerHTML = `<section class="page wrap">
    <div class="page-head">
      <div><span class="label">Collection ▪ ${paintings().length} paintings ▪ ${frames().length} frames</span>
        <h1 class="display" style="margin-top:14px">Find your painting.</h1></div>
      <p class="lead">Describe it, say it — or show us your room and let our curator choose.</p>
    </div>
    <form class="console" id="console">
      <div class="console-row">
        <input class="query" id="query" autocomplete="off" placeholder="Try “blue landscape paintings”" value="${esc(params.get("q") || "")}" aria-label="Search the collection">
        <button type="button" class="icon-btn" id="mic" title="Search by voice" aria-label="Search by voice">${icons.mic}</button>
        <button type="button" class="icon-btn" id="pick-image" title="Upload a photo of your room" aria-label="Upload a photo">${icons.image}</button>
        <button type="submit" class="btn solid">Search</button>
      </div>
      <div class="voice-panel hidden" id="voice-panel"></div>
      <div class="image-panel" id="image-panel" data-mode="room">
        ${photoDropHtml("image-drop", "upload-photo", `<button type="button" class="text-link" id="similar-photo">or find paintings similar to a photo</button>`)}
        <div id="image-preview"></div>
      </div>
      <input type="file" id="image-file" accept="image/*" hidden>
    </form>
    <div class="chips quick">${QUICK_QUERIES.map((q) => `<button type="button" class="chip" data-quick="${esc(q)}">${esc(q)}</button>`).join("")}</div>
    <div class="results-meta">
      <div class="row" id="results-meta-text"></div>
      <div class="filters">${["ALL", "PAINTING", "FRAME"].map((f) => `<button type="button" class="chip ${SearchResultView.filter === f ? "active" : ""}" data-filter="${f}">${f === "ALL" ? "All" : f === "PAINTING" ? "Paintings" : "Frames"}</button>`).join("")}</div>
    </div>
    <div id="results"></div>
  </section>`;

  const form = document.getElementById("console");
  const input = document.getElementById("query");
  const fileInput = document.getElementById("image-file");
  const panel = document.getElementById("image-panel");

  // A photo either goes to the curator ("room": UC14 picks for the room) or to the similarity search (UC04).
  // Drops and pastes always go to the curator; the small "similar" link opens the picker for UC04.
  // A room photo opens "Try it in your room" straight away: the best pick is hung on that wall.
  let pickerMode = "room";
  const runPhoto = (mode) => {
    panel.dataset.mode = mode;
    if (mode === "similar") return SearchUI.submitImage(ImageUpload.file);
    RoomPreview.requested = null;
    pendingPhoto = ImageUpload.file;
    location.hash = "#/room";
  };
  const usePhotoHere = async (file, mode = "room") => {
    if (await ImageUpload.choose(file)) runPhoto(mode);
  };
  const openPicker = (mode) => {
    pickerMode = mode;
    fileInput.click();
  };
  photoTarget = (file) => usePhotoHere(file);
  fileInput.onchange = () => {
    const file = fileInput.files[0];
    fileInput.value = "";   // choosing the same photo again still triggers a change
    usePhotoHere(file, pickerMode);
  };
  const drop = document.getElementById("image-drop");
  drop.onclick = () => openPicker("room");
  drop.onkeydown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openPicker("room");
    }
  };
  document.getElementById("similar-photo").onclick = (event) => {
    event.stopPropagation();
    openPicker("similar");
  };
  document.getElementById("pick-image").onclick = () => openPicker("room");
  document.getElementById("image-preview").onclick = (event) => {
    const toggle = event.target.closest("[data-photo-mode]");
    if (toggle && ImageUpload.file) runPhoto(toggle.dataset.photoMode);
  };

  form.onsubmit = (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (ImageUpload.file && text) SearchUI.submitMultimodal(text, ImageUpload.file);
    else SearchUI.submitText(text);
  };
  document.querySelectorAll("[data-quick]").forEach((chip) => chip.onclick = () => {
    input.value = chip.dataset.quick;
    SearchUI.submitText(chip.dataset.quick);
  });
  document.querySelectorAll("[data-filter]").forEach((chip) => chip.onclick = () => {
    SearchResultView.filter = chip.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((c) => c.classList.toggle("active", c === chip));
    SearchResultView.render(SearchResultView.results);
  });
  document.getElementById("mic").onclick = () => toggleVoice("search");

  // A new visit starts without a photo; the last room photo stays available on "Find for my room".
  ImageUpload.file = null;
  ImageUpload.dataUrl = null;
  ImageUpload.preview();
  if (params.get("q")) SearchUI.submitText(params.get("q"));
  else {
    SearchResultView.context = { label: "", seconds: 0 };
    SearchResultView.render(state.products.map((product) => ({ product })));
  }
  if (params.get("voice")) document.getElementById("mic").focus();
  if (params.get("upload")) {
    drop.scrollIntoView({ block: "center" });
    drop.focus();
  }
}

/** Painting page: the print on a wall, its facts, the frame choice and add to cart. */
function painting(params, id) {
  const product = state.byId.get(id);
  if (!product) {
    app.innerHTML = `<section class="page wrap"><div class="empty"><p class="h3">This work is not in the collection</p><a class="btn" href="#/collection">Back to the collection</a></div></section>`;
    return;
  }
  const isPainting = product.category === "PAINTING";
  let chosenFrame = null;
  let quantity = 1;
  const stock = product.stockQuantity;
  const stockClass = stock === 0 ? "out" : stock <= 3 ? "low" : "";
  const related = paintings().filter((p) => p.productId !== product.productId && isPainting &&
    (p.style === product.style || p.artist.name === product.artist.name)).slice(0, 3);
  app.innerHTML = `<section class="page wrap">
    <div class="row" style="margin-bottom:26px"><a class="link" href="#/collection">← Collection</a></div>
    <div class="detail">
      <div class="detail-wall" id="detail-wall"></div>
      <div class="detail-info">
        <span class="label">${isPainting ? `Painting ▪ ${esc(product.style)} ▪ ${esc(product.yearCreated)}` : `Frame ▪ ${esc(product.material)}`}</span>
        <h1>${esc(product.name)}</h1>
        <div class="detail-artist">${isPainting ? `${esc(product.artist.name)} — ${esc(product.artist.nationality)}, ${esc(product.artist.lifeYears)}` : esc(product.sizeLabel)}</div>
        <div class="row" style="justify-content:space-between">
          <span class="detail-price" id="detail-price">${money(product.price)}</span>
          <span class="stock ${stockClass} label"><i></i>${stock === 0 ? "Sold out" : `${stock} in stock`}</span>
        </div>
        <div class="specs">
          ${isPainting ? `<div>Size</div><div>${esc(product.widthCm)} × ${esc(product.heightCm)} cm</div>
          <div>Medium</div><div>${esc(product.medium)}</div>
          <div>Subject</div><div>${esc(cap(product.subject))}</div>
          <div>Colour</div><div>${esc(cap(product.dominantColor))}</div>` : `<div>Material</div><div>${esc(cap(product.material))}</div>
          <div>Colour</div><div>${esc(cap(product.color))}</div><div>Size</div><div>${esc(product.sizeLabel)}</div>`}
          <div>Reference</div><div class="mono">${esc(product.productId)}</div>
        </div>
        ${isPainting ? `<div class="stack"><span class="label">Frame</span><div class="frames" id="frames">
          <button type="button" class="frame-option selected" data-frame=""><span class="frame-sample" style="border:1px dashed var(--line-strong)"></span><span class="label">No frame</span><span>${money(0)}</span></button>
          ${frames().map((f) => `<button type="button" class="frame-option" data-frame="${esc(f.productId)}"><span class="frame-sample" style="background:${frameLook(f)}"></span><span class="label">${esc(f.name.replace(/ frame.*$/i, ""))}</span><span>+ ${money(f.price)}</span></button>`).join("")}
        </div></div>` : ""}
        <div class="row" style="margin-top:26px">
          <div class="qty"><button type="button" id="qty-down" aria-label="Decrease">−</button><span id="qty">1</span><button type="button" id="qty-up" aria-label="Increase">+</button></div>
          <button type="button" class="btn solid" id="add-cart" ${stock === 0 ? "disabled" : ""} style="flex:1">Add to cart</button>
        </div>
        ${isPainting ? `<a class="btn block" href="#/room?p=${esc(product.productId)}" style="margin-top:10px">Try it in my room</a>` : ""}
        <p style="margin-top:26px">${esc(product.description)}</p>
        ${isPainting ? `<p class="attribution" id="credit">Reproduction of a public-domain work. Image: Wikimedia Commons.</p>` : ""}
      </div>
    </div>
    ${related.length ? `<section class="section" style="margin-top:96px"><div class="section-head"><h2 class="h2">You may also like</h2></div>
      <div class="grid-3">${related.map((p) => productCard(p)).join("")}</div></section>` : ""}
  </section>`;

  if (isPainting) loadCredits().then((credits) => {
    const credit = credits[product.productId];
    const slot = document.getElementById("credit");
    if (credit && slot) {
      slot.innerHTML = `Reproduction of a public-domain work ▪ ${esc(credit.licence)} ▪ image via
        <a class="link" href="${esc(credit.page)}" target="_blank" rel="noopener">Wikimedia Commons ↗</a>`;
    }
  });
  const wall = document.getElementById("detail-wall");
  const drawWall = () => {
    wall.innerHTML = isPainting
      ? framedHtml(product, chosenFrame, { framePx: chosenFrame ? 18 : 0, matPx: chosenFrame ? 30 : 0, width: "min(100%, 520px)" })
      : `<div class="frame-swatch" style="width:min(70%,360px);background:${frameLook(product)}"><div></div></div>`;
    const total = Number(product.price) + (chosenFrame ? Number(chosenFrame.price) : 0);
    document.getElementById("detail-price").textContent = money(total * quantity);
  };
  drawWall();
  document.querySelectorAll("[data-frame]").forEach((button) => button.onclick = () => {
    chosenFrame = button.dataset.frame ? state.byId.get(button.dataset.frame) : null;
    document.querySelectorAll("[data-frame]").forEach((b) => b.classList.toggle("selected", b === button));
    drawWall();
  });
  const setQuantity = (value) => {
    quantity = Math.max(1, Math.min(value, stock || 1));
    document.getElementById("qty").textContent = quantity;
    drawWall();
  };
  document.getElementById("qty-down").onclick = () => setQuantity(quantity - 1);
  document.getElementById("qty-up").onclick = () => setQuantity(quantity + 1);
  document.getElementById("add-cart").onclick = async () => {
    if (state.session?.admin) return toast("Switch to a customer account to shop", true);
    try {
      await addToCart(product.productId, quantity);
      if (chosenFrame) await addToCart(chosenFrame.productId, quantity);
      toast(chosenFrame ? `Added ${product.name} with a ${chosenFrame.material} frame` : `Added ${product.name} to your cart`);
    } catch (error) {
      toast(error.message, true);
    }
  };
}

/** Find a painting for my room (UC14): the curator's picks hung on the customer's own wall. */
async function room(params) {
  const samples = await loadSampleRooms();
  RoomPreview.requested = params.get("p");
  RoomPreview.frameChosen = false;
  RoomPreview.frame = null;
  app.innerHTML = `<section class="page wrap">
    <div class="page-head">
      <div><span class="label">Find a painting for my room</span>
        <h1 class="display" style="margin-top:14px">Hang it before<br>you buy it.</h1></div>
      <p class="lead">Upload a photo of your room — our AI curator picks paintings that fit it and hangs them on your wall at their real size.</p>
    </div>
    <div class="room">
      <div>
        <div class="stage" id="stage">
          <div class="stage-empty"><p class="h2">Your wall goes here.</p>
            <p>Upload a photo of your room, or start with one of our sample rooms.</p></div>
        </div>
        <div class="try-bar">
          <div class="fit"><span class="label">Why it fits</span>
            <p id="fit-reason">Upload a photo of your room — our AI curator picks paintings that fit it and tells you why.</p></div>
          <div class="try-actions">
            <span class="price" id="room-total"></span>
            <button type="button" class="btn" id="room-save">Save image</button>
            <button type="button" class="btn solid" id="room-cart">Add to cart</button>
          </div>
        </div>
      </div>
      <aside class="room-panel">
        <section class="step">
          <div class="step-head"><span class="num">01</span><h3>Your room</h3></div>
          ${photoDropHtml("room-drop", "room-upload", `<button type="button" class="btn small" id="room-camera-btn">Take a photo</button><input type="file" id="room-camera" accept="image/*" capture="environment" hidden>`)}
          <input type="file" id="room-file" accept="image/*" hidden>
          <span class="label" style="display:block;margin-top:18px">Or try a sample room</span>
          <div class="samples">${samples.map((s, i) => `<button type="button" data-sample="${i}" title="${esc(s.label)}"><img src="${s.url}" alt="${esc(s.label)}"></button>`).join("")}</div>
          <p class="muted small-print">Your photo stays in this browser tab and is never stored on our server.</p>
        </section>
        <section class="step">
          <div class="step-head"><span class="num">02</span><h3>What we see</h3></div>
          <div id="room-reading"><p class="muted">The colours, style and mood of your room appear here.</p></div>
        </section>
        <section class="step">
          <div class="step-head"><span class="num">03</span><h3>Picked for this wall</h3></div>
          <div class="filmstrip" id="filmstrip"><p class="muted">Our curator's picks appear here.</p></div>
        </section>
        <section class="step">
          <div class="step-head"><span class="num">04</span><h3>Make it yours</h3></div>
          <div class="controls">
            <div><div class="control-row"><span class="label">How wide is this wall?</span><span class="mono" id="wall-width-value">300 cm</span></div>
              <input type="range" id="wall-width" min="150" max="600" step="10" value="300" aria-label="Wall width in centimetres"></div>
            <div><div class="control-row"><span class="label">Print size</span><span class="mono" id="painting-width-value">—</span></div>
              <input type="range" id="painting-width" min="30" max="160" step="1" value="60" aria-label="Print width in centimetres"></div>
            <div class="stack" style="gap:8px"><span class="label">Frame</span><div class="frame-pills">${framePillsHtml()}</div></div>
            <div class="row" style="justify-content:space-between">
              <label class="row label" style="gap:8px"><input type="checkbox" id="mat-toggle" checked> Passe-partout</label>
              <label class="row label" style="gap:8px"><input type="checkbox" id="light-toggle" checked> Match room light</label>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </section>`;
  wireRoomControls();
  document.getElementById("room-upload").onclick = (event) => {
    event.stopPropagation();
    document.getElementById("room-file").click();
  };
  photoTarget = (file) => RoomPreview.chooseRoom(file);
  const sample = params.get("sample");
  if (pendingPhoto) {
    const file = pendingPhoto;
    pendingPhoto = null;
    RoomPreview.chooseRoom(file);
  } else if (sample !== null && sample !== "") {
    document.querySelector(`[data-sample="${Number(sample)}"]`)?.click();
  } else {
    restoreRoom();
  }
}

async function cart() {
  app.innerHTML = `<section class="page wrap">
    <div class="page-head"><div><span class="label">Your cart</span><h1 class="display" style="margin-top:14px">Cart.</h1></div></div>
    <div id="cart-view"><div class="loading"><span class="spinner"></span>Loading your cart</div></div>
  </section>`;
  if (state.session?.admin) {
    document.getElementById("cart-view").innerHTML = `<div class="empty"><p class="h3">This is a staff account</p><p>Switch to a customer account in the account menu to shop.</p></div>`;
    return;
  }
  const [current] = await Promise.all([api("/api/cart"), refreshSession()]);
  CartView.render(current);
}

async function orders(params) {
  app.innerHTML = `<section class="page wrap">
    <div class="page-head"><div><span class="label">My orders ▪ ${esc(state.session?.name || "")}</span>
      <h1 class="display" style="margin-top:14px">Orders.</h1></div>
      <p class="lead">Follow each order from placed to delivered. You can cancel any order until it ships.</p></div>
    <div class="orders-layout">
      <div id="order-list"><div class="loading"><span class="spinner"></span>Loading your orders</div></div>
      <aside class="summary">
        <span class="label">Find an order</span>
        <form class="lookup" id="lookup" style="margin-top:14px">
          <input class="input" id="lookup-id" placeholder="Order id, e.g. 20261001" autocomplete="off">
          <button type="submit" class="btn solid">Look up</button>
        </form>
        <div id="lookup-result"></div>
        <div class="divider"></div>
        <span class="label">Or just ask</span>
        <p class="muted" style="margin:10px 0 14px">“Where is my latest order?”</p>
        <button type="button" class="btn block" data-open-assistant>Ask the assistant</button>
      </aside>
    </div>
  </section>`;
  if (state.session?.admin) {
    document.getElementById("order-list").innerHTML = `<div class="empty"><p class="h3">This is a staff account</p><p>Customer orders are in the <a class="link" href="#/admin?tab=orders">back office</a>.</p></div>`;
    return;
  }
  document.getElementById("lookup").onsubmit = (event) => {
    event.preventDefault();
    OrderView.lookup(document.getElementById("lookup-id").value);
  };
  bindAssistantButtons();
  OrderView.render(await api("/api/orders"));
  if (params.get("lookup")) {
    document.getElementById("lookup-id").value = params.get("lookup");
    OrderView.lookup(params.get("lookup"));
  }
  if (params.get("assistant")) openAssistant();
}

async function admin(params) {
  if (!state.session?.admin) {
    app.innerHTML = `<section class="page wrap"><div class="empty"><p class="h3">Staff only</p>
      <p>Switch to the gallery staff account in the account menu.</p></div></section>`;
    return;
  }
  const tab = params.get("tab") || "products";
  app.innerHTML = `<section class="page wrap">
    <div class="page-head"><div><span class="label">Back office</span>
      <h1 class="display" style="margin-top:14px">Gallery admin.</h1></div>
      <p class="lead">Keep prices and stock up to date, add new paintings and move orders along.</p></div>
    <div class="tabs"><button type="button" data-tab="products" class="${tab === "products" ? "active" : ""}">Paintings &amp; frames</button>
      <button type="button" data-tab="orders" class="${tab === "orders" ? "active" : ""}">Orders</button></div>
    <div id="admin-body"><div class="loading"><span class="spinner"></span>Loading</div></div>
  </section>`;
  document.querySelectorAll("[data-tab]").forEach((button) => button.onclick = () => {
    location.hash = `#/admin?tab=${button.dataset.tab}`;
  });
  if (tab === "orders") AdminView.renderOrders(await api("/api/admin/orders"));
  else AdminView.renderProducts(await api("/api/admin/products"));
}

// ------------------------------------------------------------- voice input

let recordTimer;
function toggleVoice(target) {
  if (VoiceInput.recorder && VoiceInput.recorder.state === "recording") {
    VoiceInput.stop();
    return;
  }
  VoiceInput.target = target;
  VoiceInput.start();
}

window.addEventListener("voice", (event) => {
  const { status, target, message, transcript } = event.detail;
  const button = document.getElementById(target === "assistant" ? "assistant-mic" : "mic");
  clearInterval(recordTimer);
  button?.classList.toggle("recording", status === "recording");
  if (target === "assistant") {
    const input = document.getElementById("assistant-input");
    if (status === "recording") input.placeholder = "Listening… tap the microphone when you're done";
    if (status === "transcribing") input.placeholder = "Just a moment…";
    if (status === "error") { input.placeholder = "Ask about a painting or your order…"; toast(message, true); }
    return;
  }
  const panel = document.getElementById("voice-panel");
  if (!panel) return;
  panel.classList.remove("hidden");
  if (status === "recording") {
    const started = Date.now();
    panel.innerHTML = `<span class="rec-timer" id="rec-timer">● 0:00</span><span class="voice-status">Listening…</span>
      <span class="muted">Tap the microphone when you're done</span>`;
    recordTimer = setInterval(() => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      const timer = document.getElementById("rec-timer");
      if (timer) timer.textContent = `● 0:${String(seconds).padStart(2, "0")}`;
    }, 250);
  } else if (status === "transcribing") {
    panel.innerHTML = `<span class="spinner"></span><span class="voice-status">Just a moment…</span>`;
  } else if (status === "error") {
    panel.innerHTML = `<span class="voice-status">${esc(message)}</span>
      <button type="button" class="text-link" id="voice-retry">Try again</button>`;
    document.getElementById("voice-retry").onclick = () => toggleVoice("search");
  } else if (status === "done") {
    showTranscript(transcript);
  }
});

/** The transcript is editable before the voice search runs (FR02). */
function showTranscript(transcript) {
  const panel = document.getElementById("voice-panel");
  if (!panel) return;
  panel.classList.remove("hidden");
  panel.innerHTML = `<span class="label">We heard</span>
    <input class="transcript" id="transcript" value="${esc(transcript)}" aria-label="What we heard — you can edit it">
    <button type="button" class="btn solid" id="voice-search">Search</button>`;
  const field = document.getElementById("transcript");
  document.getElementById("voice-search").onclick = () => SearchUI.submitVoice(field.value);
  field.onkeydown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      SearchUI.submitVoice(field.value);
    }
  };
}

VoiceInput.onTranscript((transcript, target) => {
  if (target === "assistant") {
    const input = document.getElementById("assistant-input");
    input.value = transcript;
    input.placeholder = "Ask about a painting or your order…";
    input.focus();
  }
});

// --------------------------------------------------------------- assistant

function openAssistant() {
  document.body.classList.add("drawer-open");
  setTimeout(() => document.getElementById("assistant-input").focus(), 300);
}
function closeAssistant() {
  document.body.classList.remove("drawer-open");
}
function bindAssistantButtons() {
  document.querySelectorAll("[data-open-assistant]").forEach((button) => button.onclick = openAssistant);
}

function setupAssistant() {
  bindAssistantButtons();
  document.getElementById("assistant-close").onclick = closeAssistant;
  document.getElementById("drawer-backdrop").onclick = closeAssistant;
  document.addEventListener("keydown", (event) => event.key === "Escape" && closeAssistant());
  const suggestions = ["Where is my latest order?", "Find my order 20261001", "A calm blue painting under 100 dollars"];
  const slot = document.getElementById("assistant-suggestions");
  slot.innerHTML = suggestions.map((s) => `<button type="button" class="chip" data-ask="${esc(s)}">${esc(s)}</button>`).join("");
  slot.querySelectorAll("[data-ask]").forEach((chip) => chip.onclick = () => AssistantView.send(chip.dataset.ask));
  document.getElementById("assistant-form").onsubmit = (event) => {
    event.preventDefault();
    const input = document.getElementById("assistant-input");
    AssistantView.send(input.value);
    input.value = "";
  };
  document.getElementById("assistant-mic").onclick = () => toggleVoice("assistant");
  document.getElementById("chat").innerHTML = `<div class="msg bot"><div class="bubble">Hello! I can help you find a painting or check on an order. Ask me anything — or tap one of the suggestions below.</div></div>`;
}

// ------------------------------------------------------------ header bits

function renderAccount(session) {
  const current = ACCOUNTS.find((account) => account.id === session?.customerId);
  document.getElementById("account-name").textContent = current ? current.name : "Sign in";
  document.getElementById("cart-count").textContent = session?.cartCount ?? 0;
  document.getElementById("nav-admin").classList.toggle("hidden", !session?.admin);
  const links = session?.admin
    ? `<a href="#/admin">Paintings &amp; stock</a><a href="#/admin?tab=orders">Customer orders</a>`
    : `<a href="#/orders">My orders</a><a href="#/cart">My cart</a>`;
  const menu = document.getElementById("account-menu");
  menu.innerHTML = `<div class="account-head"><span class="label">Signed in as</span>
      <strong>${esc(current?.name || "Guest")}</strong><small>${esc(current?.role || "")}</small></div>
    <nav class="account-links">${links}</nav>
    <div class="label account-switch">Switch account</div>` +
    ACCOUNTS.filter((account) => account.id !== session?.customerId).map((account) =>
      `<button type="button" data-account="${account.id}"><span>${esc(account.name)}<small>${esc(account.role)}</small></span><span aria-hidden="true">→</span></button>`).join("");
  menu.querySelectorAll("a").forEach((link) => link.onclick = () => document.getElementById("account").classList.remove("open"));
  menu.querySelectorAll("[data-account]").forEach((button) => button.onclick = async () => {
    document.getElementById("account").classList.remove("open");
    await login(button.dataset.account);
    toast(`Welcome, ${ACCOUNTS.find((a) => a.id === button.dataset.account).name}`);
    if (button.dataset.account === "ADMIN") location.hash = "#/admin";
    else if (location.hash.startsWith("#/admin")) location.hash = "#/";
    else route();
  });
}

function setupHeader() {
  const header = document.getElementById("header");
  window.addEventListener("scroll", () => header.classList.toggle("scrolled", window.scrollY > 40), { passive: true });
  document.getElementById("account-button").onclick = (event) => {
    event.stopPropagation();
    document.getElementById("account").classList.toggle("open");
  };
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#account")) document.getElementById("account").classList.remove("open");
  });
  document.getElementById("theme-toggle").onclick = () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("hoa-theme", next); } catch (e) { /* private mode: keep it for this visit */ }
  };
  document.getElementById("menu-toggle").onclick = () => header.classList.toggle("menu-open");
}

/** Small “decoding” animation for monospace captions, in the spirit of fustic.studio. */
function scramble(element) {
  if (!element) return;
  const final = element.textContent;
  const glyphs = "▪01ABCDEFGHIKLMNOPRSTUVWXY";
  let frame = 0;
  const timer = setInterval(() => {
    frame += 1;
    element.textContent = final.split("").map((c, i) => (c === " " || i < frame * 1.4 ? c : glyphs[(i * 7 + frame) % glyphs.length])).join("");
    if (frame * 1.4 >= final.length) {
      clearInterval(timer);
      element.textContent = final;
    }
  }, 40);
}

// ------------------------------------------------------- photos anywhere

/** Drop or paste a photo anywhere: it goes to the photo field of the page (or opens "Find for my room"). */
function setupPhotoDrop() {
  let depth = 0;
  const hasFiles = (event) => [...(event.dataTransfer?.types || [])].includes("Files");
  const stop = () => {
    depth = 0;
    document.body.classList.remove("dragging-file");
  };
  window.addEventListener("dragenter", (event) => {
    if (!hasFiles(event)) return;
    depth += 1;
    document.body.classList.add("dragging-file");
  });
  window.addEventListener("dragleave", (event) => {
    if (!hasFiles(event)) return;
    depth = Math.max(0, depth - 1);
    if (!depth) stop();
  });
  window.addEventListener("dragover", (event) => {
    if (!hasFiles(event)) return;
    event.preventDefault();   // otherwise the browser opens the image in a new tab
    event.dataTransfer.dropEffect = "copy";
  });
  window.addEventListener("drop", (event) => {
    if (!hasFiles(event)) return;
    event.preventDefault();
    stop();
    usePhoto(event.dataTransfer.files[0]);
  });
  window.addEventListener("paste", (event) => {
    const item = [...(event.clipboardData?.items || [])].find((i) => i.kind === "file" && i.type.startsWith("image/"));
    if (!item) return;   // ordinary text paste
    event.preventDefault();
    usePhoto(item.getAsFile());
  });
}

function usePhoto(file) {
  if (!file) return;
  if (photoTarget) {
    photoTarget(file);
    return;
  }
  pendingPhoto = file;
  location.hash = "#/room";
}

// ------------------------------------------------------------------- start

async function start() {
  setupHeader();
  setupAssistant();
  setupPhotoDrop();
  setDeveloper(developer.on);
  document.addEventListener("keydown", (event) => {
    // Shift + D shows the developer view (scores, AI mode, tools) for the report and the Q&A.
    if (event.shiftKey && event.key === "D" && !event.target.closest("input, textarea, select")) setDeveloper(!developer.on);
  });
  onSession(renderAccount);
  await refreshSession();
  if (!state.session.customerId) await login("C001");   // the shop opens signed in as the VIP customer
  await loadProducts();
  window.addEventListener("hashchange", route);
  await route();
}

start().catch(() => {
  app.innerHTML = `<section class="page wrap"><div class="empty"><p class="h3">We can't reach the gallery right now</p>
    <p>Please check your connection and reload the page.</p></div></section>`;
});
