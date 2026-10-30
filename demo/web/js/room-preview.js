// RoomPreview (model view, UC14 "Find Painting for My Room"): the customer shows a photo of a room,
// Gemma 4 reads its palette and style (SearchService.describeRoom), SearchService.searchRoom suggests
// paintings, and the chosen painting is previewed on the wall at its real size with a frame.
// The room photo stays in this browser tab (memory and sessionStorage); nothing is stored on the server.
import {
  addToCart, api, esc, frames, frameLook, frameStops, framedHtml, MAX_UPLOAD_BYTES, money, note, state, toast, toJpeg,
} from "./core.js";

/** Sample rooms (CC0 photos); the real list with curated wall boxes is /img/rooms/rooms.json. */
let SAMPLE_ROOMS = [
  { url: "/img/rooms/room1.jpg", label: "Bright living room", wallBox: [0.3, 0.1, 0.4, 0.42] },
  { url: "/img/rooms/room2.jpg", label: "Brick-wall apartment", wallBox: [0.5, 0.1, 0.3, 0.42] },
  { url: "/img/rooms/room3.jpg", label: "Afternoon light", wallBox: [0.4, 0.08, 0.45, 0.38] },
];
const DEFAULT_BOX = [0.33, 0.08, 0.34, 0.4];   // upper-centre third of the photo
const FRAME_CM = 3.2;   // visible width of a frame moulding
const MAT_CM = 6;       // width of the passe-partout

export const RoomPreview = {
  room: null,          // {image, dataUrl, wallBox}
  reading: null,       // what Gemma 4 read from the room
  suggestions: [],
  painting: null,      // the Product on the wall
  frame: null,         // the chosen Frame product, or null
  frameChosen: false,  // true once the customer picked a frame (or no frame) themselves
  sampleBox: null,     // free-wall box of a sample room, used if Gemma does not return one
  mat: true,
  matchLight: true,
  wallWidthCm: 300,
  paintingWidthCm: 60,
  position: { x: 0.5, y: 0.35 },
  brightness: 1,
  requested: null,     // painting id asked for in the URL (#/room?p=P05)

  /** Loads the room photo, asks Gemma 4 to read it and fetches the suggestions. */
  async chooseRoom(file) {
    if (!file) return;
    let photo;
    try {
      photo = await toJpeg(file);   // HEIC, GIF, huge PNG… become a JPEG of at most 1600 px
    } catch (error) {
      toast("We can't open this file — please choose a JPEG or PNG photo of your room", true);
      return;
    }
    if (photo.file.size > MAX_UPLOAD_BYTES) {
      toast("This photo is still larger than 5 MB — please choose a smaller one", true);
      return;
    }
    // Sample rooms carry a curated wall box; for the customer's own photo we trust Gemma's box if plausible.
    this.room = { image: photo.image, dataUrl: photo.dataUrl, wallBox: this.sampleBox || DEFAULT_BOX, curated: Boolean(this.sampleBox) };
    this.sampleBox = null;
    this.reading = null;
    this.suggestions = [];
    this.painting = null;
    this.brightness = measureBrightness(photo.image, this.room.wallBox);
    saveRoom(this, true);
    drawStage(this);
    renderReading(null, "loading");
    renderWaiting("loading");
    const started = performance.now();
    try {
      const reading = await api("/api/room/describe", { method: "POST", body: { image: photo.dataUrl } });
      this.reading = reading;
      const box = parseBox(reading.wall_box);
      if (box && !this.room.curated) this.room.wallBox = box;
      this.brightness = measureBrightness(photo.image, this.room.wallBox);
      renderReading(reading);
      const results = await api("/api/room/search", { method: "POST", body: { image: photo.dataUrl } });
      note({ request: "room", ai: reading.ai, looking_for: `${reading.style} ▪ ${reading.subject} ▪ ${reading.color}`,
        wall_box: reading.wall_box || "none", results: results.length, seconds: (performance.now() - started) / 1000 });
      this.renderSuggestions(results);
    } catch (error) {
      note({ request: "room", error: error.message });
      renderReading(null, "error", error.message);
      renderWaiting("error", error.message);
    }
  },

  /** Hangs one painting on the wall, centred in the free wall area. */
  placePainting(product) {
    if (!product || !this.room) return;
    this.painting = product;
    this.paintingWidthCm = product.widthCm || 60;
    const [x, y, w, h] = this.room.wallBox;
    this.position = { x: x + w / 2, y: y + h / 2 };
    if (this.frame === null && !this.frameChosen) this.frame = frames().find((f) => f.material === "aluminium") || null;
    syncControls(this);
    updateHang(this);
    document.querySelectorAll(".film").forEach((film) =>
      film.classList.toggle("selected", film.dataset.product === product.productId));
    const fit = document.getElementById("fit-reason");
    const result = this.suggestions.find((r) => r.product.productId === product.productId);
    if (fit) fit.textContent = whyItFits(result || { product }, this.reading);
    saveRoom(this);
  },

  /** Shows the suggested paintings as a filmstrip, in the curator's order, and hangs the first one. */
  renderSuggestions(results) {
    let list = (results || []).filter((r) => r.product.category === "PAINTING");
    if (this.requested && state.byId.has(this.requested)) {
      const found = list.find((r) => r.product.productId === this.requested);
      list = [found || { product: state.byId.get(this.requested), score: 0, reason: "", requested: true },
        ...list.filter((r) => r !== found)];
    }
    this.suggestions = list.slice(0, 10);
    const strip = document.getElementById("filmstrip");
    if (!strip) return;
    if (!this.suggestions.length) {
      strip.innerHTML = `<p class="muted">No suggestions for this photo — try another one.</p>`;
      return;
    }
    strip.innerHTML = this.suggestions.map((r, i) => `
      <button type="button" class="film" data-product="${esc(r.product.productId)}" title="${esc(whyItFits(r, this.reading))}">
        <span class="thumb"><img src="${esc(r.product.imageUrl)}" alt=""></span>
        <b>${esc(r.product.name)}</b>
        <small>${r.product.productId === this.requested ? "Your pick ▪ " : i === 0 ? "Best match ▪ " : ""}${money(r.product.price)}</small>
        <span class="dev dev-note">S ${(r.score || 0).toFixed(3)}</span>
      </button>`).join("");
    strip.querySelectorAll(".film").forEach((button) =>
      button.onclick = () => this.placePainting(state.byId.get(button.dataset.product)));
    this.placePainting(this.suggestions[0].product);
  },
};

// -------------------------------------------------------------- private helpers

function parseBox(text) {
  const values = String(text || "").split(",").map(Number);
  if (values.length !== 4 || values.some((v) => !Number.isFinite(v) || v < 0 || v > 1)) return null;
  if (values[2] < 0.08 || values[3] < 0.08) return null;
  return values;
}

/** Average luminance of the wall area, turned into a CSS brightness so the print matches the room light. */
function measureBrightness(image, box) {
  const canvas = document.createElement("canvas");
  canvas.width = 48;
  canvas.height = 48;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  const [x, y, w, h] = box;
  context.drawImage(image, x * image.naturalWidth, y * image.naturalHeight,
    w * image.naturalWidth, h * image.naturalHeight, 0, 0, 48, 48);
  const pixels = context.getImageData(0, 0, 48, 48).data;
  let total = 0;
  for (let i = 0; i < pixels.length; i += 4) total += 0.2126 * pixels[i] + 0.7152 * pixels[i + 1] + 0.0722 * pixels[i + 2];
  const luminance = total / (pixels.length / 4) / 255;
  return Math.min(1.04, Math.max(0.74, 0.7 + luminance * 0.42));
}

function drawStage(view) {
  const stage = document.getElementById("stage");
  if (!stage) return;
  stage.innerHTML = `<img class="room-photo" src="${view.room.dataUrl}" alt="Your room">
    <div class="hang hidden" id="hang"></div>
    <div class="stage-caption" id="stage-caption"></div>`;
  enableDrag(view, stage);
}

/** Positions and sizes the painting from real centimetres: pixels per cm = stage width / wall width. */
function updateHang(view) {
  const stage = document.getElementById("stage");
  const hang = document.getElementById("hang");
  if (!stage || !hang || !view.painting) return;
  const stageWidth = stage.clientWidth;
  const pxPerCm = stageWidth / view.wallWidthCm;
  const frame = view.frame;
  const framePx = frame ? Math.max(2, FRAME_CM * pxPerCm) : 0;
  const matPx = view.mat ? Math.max(3, MAT_CM * pxPerCm) : 0;
  const width = view.paintingWidthCm * pxPerCm + 2 * (framePx + matPx);
  hang.classList.remove("hidden");
  hang.style.width = `${width}px`;
  hang.style.left = `${view.position.x * 100}%`;
  hang.style.top = `${view.position.y * 100}%`;
  hang.innerHTML = framedHtml(view.painting, frame, { framePx, matPx }) +
    `<span class="handle">Drag to move</span>`;
  hang.querySelector(".framed").style.filter = view.matchLight ? `brightness(${view.brightness.toFixed(2)})` : "";
  const height = Math.round(view.paintingWidthCm * (view.painting.heightCm || 1) / (view.painting.widthCm || 1));
  const caption = document.getElementById("stage-caption");
  if (caption) caption.textContent = `${view.painting.name} ▪ ${Math.round(view.paintingWidthCm)} × ${height} cm ▪ ${frame ? frame.name.replace(/ \d+ x \d+$/, "") : "No frame"}`;
  const total = document.getElementById("room-total");
  if (total) total.textContent = money(Number(view.painting.price) + (frame ? Number(frame.price) : 0));
}

function enableDrag(view, stage) {
  let drag = null;
  stage.onpointerdown = (event) => {
    const hang = event.target.closest(".hang");
    if (!hang) return;
    const rect = stage.getBoundingClientRect();
    drag = { dx: event.clientX - (rect.left + view.position.x * rect.width), dy: event.clientY - (rect.top + view.position.y * rect.height) };
    stage.setPointerCapture(event.pointerId);
  };
  stage.onpointermove = (event) => {
    if (!drag) return;
    const rect = stage.getBoundingClientRect();
    view.position.x = Math.min(0.97, Math.max(0.03, (event.clientX - drag.dx - rect.left) / rect.width));
    view.position.y = Math.min(0.97, Math.max(0.03, (event.clientY - drag.dy - rect.top) / rect.height));
    const hang = document.getElementById("hang");
    hang.style.left = `${view.position.x * 100}%`;
    hang.style.top = `${view.position.y * 100}%`;
  };
  stage.onpointerup = () => { drag = null; };
}

function renderReading(reading, status = "done", message = "") {
  const slot = document.getElementById("room-reading");
  if (!slot) return;
  if (status === "loading") {
    slot.innerHTML = `<div class="loading slim"><span class="spinner"></span>Looking at your room…</div>`;
    return;
  }
  if (status === "error") {
    slot.innerHTML = `<div class="notice error"><span>${esc(message)}. Try another photo, or start with one of our sample rooms.</span></div>`;
    return;
  }
  const local = reading.ai !== "gemma";
  const palette = String(reading.palette || "").split(",").map((hex) => hex.trim()).filter((hex) => /^#[0-9a-f]{6}$/i.test(hex));
  const tags = local ? [] : [reading.room, reading.tone && `${reading.tone} tones`, reading.interior, reading.mood, reading.light && `${reading.light} light`];
  const sentence = local ? "We matched paintings to the main colours of your room." : reading.reading;
  slot.innerHTML = `<div class="palette">${palette.map((hex) => `<i style="background:${hex}" title="${hex}"></i>`).join("")}</div>
    ${tags.filter(Boolean).length ? `<div class="tag">${tags.filter(Boolean).map(esc).join(' <span class="sep">▪</span> ')}</div>` : ""}
    <p class="reading">${esc(sentence || "")}</p>
    <div class="dev dev-note">ai ${esc(reading.ai)} ▪ looking for ${esc(reading.style)} ▪ ${esc(reading.subject)} ▪ ${esc(reading.color)}
      ▪ wall box ${esc(reading.wall_box || "none")}${local ? ` ▪ ${esc(reading.reading)}` : ""}</div>`;
}

/** Loading and error states of the filmstrip. */
function renderWaiting(status, message = "") {
  const strip = document.getElementById("filmstrip");
  if (!strip) return;
  strip.innerHTML = status === "loading"
    ? `<div class="loading slim"><span class="spinner"></span>Our curator is choosing paintings for your room…</div>`
    : `<p class="muted">${esc(message)}. Please try again.</p>`;
}

const SUBJECT_WORDS = { flowers: "flower painting", cityscape: "city view", "everyday life": "everyday scene", abstract: "abstract work" };

/**
 * "Why it fits" as one readable sentence. A sentence in SearchResult.reason is shown as it is; when the
 * reason is only tags ("Gemma 4 vision ▪ Impressionism ▪ blue ▪ 67% visual match") it is written from the
 * painting and the room reading.
 */
function whyItFits(result, reading) {
  const reason = String(result?.reason || "").trim();
  if (reason && !reason.includes("▪") && reason.split(/\s+/).length >= 6) return reason;
  const painting = result.product;
  if (result.requested) {
    return "Here is the painting you chose, on your own wall. Our curator's own picks for this room are in the strip on the right.";
  }
  const colour = String(painting.dominantColor || "").toLowerCase();
  const subject = String(painting.subject || "").toLowerCase();
  const roomColours = String(reading?.colors || "").toLowerCase();
  const tone = String(reading?.tone || "").toLowerCase();
  const first = roomColours.includes(colour)
    ? `Its ${colour} tones echo the ${colour} already in your room`
    : `Its ${colour} tones sit well with your ${tone ? `${tone} ` : ""}palette`;
  const place = [reading?.light, reading?.room].filter(Boolean).join(" ").toLowerCase() || "room";
  const what = SUBJECT_WORDS[subject] || subject || "painting";
  const mood = reading?.mood ? `keeps the ${String(reading.mood).toLowerCase()} mood of this ${place}` : `suits this ${place}`;
  return `${first}, and this ${what} ${mood}.`;
}

/** Keeps the sliders, frame pills and toggles in step with the view state. */
function syncControls(view) {
  const wall = document.getElementById("wall-width");
  const size = document.getElementById("painting-width");
  if (!wall || !size) return;
  wall.value = view.wallWidthCm;
  size.value = view.paintingWidthCm;
  document.getElementById("wall-width-value").textContent = `${view.wallWidthCm} cm`;
  const height = Math.round(view.paintingWidthCm * (view.painting?.heightCm || 1) / (view.painting?.widthCm || 1));
  document.getElementById("painting-width-value").textContent = `${Math.round(view.paintingWidthCm)} × ${height} cm`;
  document.querySelectorAll(".frame-pill").forEach((pill) =>
    pill.classList.toggle("selected", (pill.dataset.frame || "") === (view.frame?.productId || "")));
  document.getElementById("mat-toggle").checked = view.mat;
  document.getElementById("light-toggle").checked = view.matchLight;
}

/** Page wiring helper (not part of the model class): connects the room page controls once. */
export function wireRoomControls() {
  const view = RoomPreview;
  const fileInput = document.getElementById("room-file");
  const cameraInput = document.getElementById("room-camera");
  const pick = (input) => {
    const file = input.files[0];
    input.value = "";   // choosing the same photo again still triggers a change
    if (file) view.chooseRoom(file);
  };
  fileInput.onchange = () => pick(fileInput);
  cameraInput.onchange = () => pick(cameraInput);
  const drop = document.getElementById("room-drop");
  drop.onclick = (event) => {
    if (!event.target.closest("label")) fileInput.click();   // the camera button has its own input
  };
  drop.onkeydown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  };
  document.querySelectorAll("[data-sample]").forEach((button) => button.onclick = async () => {
    const sample = SAMPLE_ROOMS[Number(button.dataset.sample)];
    const blob = await (await fetch(sample.url)).blob();
    view.sampleBox = sample.wallBox;
    view.chooseRoom(new File([blob], sample.url.split("/").pop(), { type: blob.type || "image/jpeg" }));
  });
  const wall = document.getElementById("wall-width");
  const size = document.getElementById("painting-width");
  wall.oninput = () => { view.wallWidthCm = Number(wall.value); syncControls(view); updateHang(view); };
  size.oninput = () => { view.paintingWidthCm = Number(size.value); syncControls(view); updateHang(view); };
  document.querySelectorAll(".frame-pill").forEach((pill) => pill.onclick = () => {
    view.frame = pill.dataset.frame ? state.byId.get(pill.dataset.frame) : null;
    view.frameChosen = true;
    syncControls(view);
    updateHang(view);
  });
  document.getElementById("mat-toggle").onchange = (event) => { view.mat = event.target.checked; updateHang(view); };
  document.getElementById("light-toggle").onchange = (event) => { view.matchLight = event.target.checked; updateHang(view); };
  document.getElementById("room-save").onclick = () => saveImage(view);
  document.getElementById("room-cart").onclick = () => addHangingToCart(view);
  window.onresize = () => updateHang(view);
}

/**
 * Page helper (not part of the model class): shows the room photo the customer already uploaded, e.g. after
 * "Try it in my room" on a painting page, so the painting is hung on that wall at once. After a reload the
 * photo comes back from this browser tab (sessionStorage).
 */
export async function restoreRoom() {
  const view = RoomPreview;
  if (!view.room && !(await loadRoom(view))) return false;
  if (!document.getElementById("stage")) return false;   // the customer left the page meanwhile
  const hung = view.painting;
  drawStage(view);
  if (view.reading) renderReading(view.reading);
  view.renderSuggestions(view.suggestions);
  if (!view.requested && hung) view.placePainting(hung);
  return true;
}

const ROOM_KEY = "hoa-room";

/** Keeps the room photo, Gemma's reading and the picks in this browser tab only; nothing goes to the server. */
function saveRoom(view, withPhoto = false) {
  try {
    if (withPhoto) sessionStorage.setItem(`${ROOM_KEY}-photo`, view.room.dataUrl);
    sessionStorage.setItem(ROOM_KEY, JSON.stringify({
      wallBox: view.room.wallBox,
      curated: view.room.curated,
      reading: view.reading,
      suggestions: view.suggestions.filter((r) => !r.requested),
      painting: view.painting?.productId || null,
    }));
  } catch (error) {
    // storage full or blocked: the room stays in memory for this visit
  }
}

async function loadRoom(view) {
  try {
    const dataUrl = sessionStorage.getItem(`${ROOM_KEY}-photo`);
    const saved = JSON.parse(sessionStorage.getItem(ROOM_KEY) || "null");
    if (!dataUrl || !saved) return false;
    const image = new Image();
    image.src = dataUrl;
    await image.decode();
    view.room = { image, dataUrl, wallBox: saved.wallBox || DEFAULT_BOX, curated: Boolean(saved.curated) };
    view.reading = saved.reading;
    view.suggestions = (saved.suggestions || [])
      .map((r) => ({ ...r, product: state.byId.get(r.product.productId) || r.product }));
    view.painting = saved.painting ? state.byId.get(saved.painting) || null : null;
    view.brightness = measureBrightness(image, view.room.wallBox);
    return true;
  } catch (error) {
    return false;
  }
}

/** Page helper (not part of the model class): loads the sample rooms published by the backend. */
export async function loadSampleRooms() {
  try {
    const rooms = await (await fetch("/img/rooms/rooms.json")).json();
    SAMPLE_ROOMS = rooms.map((room) => ({ url: room.imageUrl, label: room.label, wallBox: room.wallBox }));
  } catch (error) {
    // keep the built-in list
  }
  return SAMPLE_ROOMS;
}

/** Composes the room photo and the framed painting on a canvas and downloads it as a PNG. */
async function saveImage(view) {
  if (!view.room || !view.painting) return toast("Choose a room and a painting first", true);
  const stage = document.getElementById("stage");
  const room = view.room.image;
  const canvas = document.createElement("canvas");
  canvas.width = room.naturalWidth;
  canvas.height = room.naturalHeight;
  const context = canvas.getContext("2d");
  context.drawImage(room, 0, 0);
  const scale = room.naturalWidth / stage.clientWidth;
  const pxPerCm = (stage.clientWidth / view.wallWidthCm) * scale;
  const framePx = view.frame ? Math.max(2, FRAME_CM * pxPerCm) : 0;
  const matPx = view.mat ? Math.max(3, MAT_CM * pxPerCm) : 0;
  const art = new Image();
  art.src = view.painting.imageUrl;
  await art.decode();
  const artW = view.paintingWidthCm * pxPerCm;
  const artH = artW * (art.naturalHeight / art.naturalWidth);
  const outerW = artW + 2 * (framePx + matPx);
  const outerH = artH + 2 * (framePx + matPx);
  const left = view.position.x * canvas.width - outerW / 2;
  const top = view.position.y * canvas.height - outerH / 2;
  context.save();
  context.shadowColor = "rgba(0,0,0,0.42)";
  context.shadowBlur = 40 * scale / 2;
  context.shadowOffsetY = 18 * scale / 2;
  const stops = frameStops(view.frame);
  if (stops) {
    const gradient = context.createLinearGradient(left, top, left + outerW, top + outerH);
    stops.forEach((colour, i) => gradient.addColorStop(i / (stops.length - 1), colour));
    context.fillStyle = gradient;
  } else {
    context.fillStyle = view.mat ? "#f3f0e8" : "rgba(0,0,0,0)";
  }
  context.fillRect(left, top, outerW, outerH);
  context.restore();
  if (view.mat) {
    context.fillStyle = "#f3f0e8";
    context.fillRect(left + framePx, top + framePx, outerW - 2 * framePx, outerH - 2 * framePx);
  }
  context.filter = view.matchLight ? `brightness(${view.brightness.toFixed(2)})` : "none";
  context.drawImage(art, left + framePx + matPx, top + framePx + matPx, artW, artH);
  context.filter = "none";
  const link = document.createElement("a");
  link.download = `hoa-${view.painting.productId}-in-my-room.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
  toast("Saved — the picture is in your downloads");
}

/** The painting on the wall plus its frame go to the cart together. */
async function addHangingToCart(view) {
  if (!view.painting) return toast("Choose a room and a painting first", true);
  try {
    await addToCart(view.painting.productId);
    if (view.frame) await addToCart(view.frame.productId);
    toast(view.frame ? `Added ${view.painting.name} with the ${view.frame.name.replace(/ \d+ x \d+$/, "")}` : `Added ${view.painting.name} to your cart`);
  } catch (error) {
    toast(error.message, true);
  }
}

/** Page helper (not part of the model class): HTML of the frame pills. */
export function framePillsHtml() {
  const options = [{ productId: "", name: "No frame" }, ...frames()];
  return options.map((frame) => `<button type="button" class="frame-pill" data-frame="${esc(frame.productId)}">
      <i style="background:${frame.productId ? frameLook(frame) : "transparent"}"></i>${esc(frame.name.replace(/ frame \d+ x \d+$/i, "").replace(/ \d+ x \d+$/, ""))}</button>`).join("");
}
