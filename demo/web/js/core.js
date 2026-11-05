// Shared helpers of the browser views: API calls, session state, formatting and small HTML templates.
// The views never touch the database; every read and write goes through the JSON API of WebServer.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/** Calls the Java API. `body` is sent as JSON, `raw` as {data, type} for audio uploads. */
export async function api(path, { method = "GET", body, raw } = {}) {
  const options = { method, headers: {}, credentials: "same-origin" };
  if (raw) {
    options.body = raw.data;
    options.headers["Content-Type"] = raw.type || "application/octet-stream";
  } else if (body !== undefined) {
    options.body = JSON.stringify(body);
    options.headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.error || response.statusText, response.status);
  return data;
}

// ------------------------------------------------------------------ state

export const state = {
  session: null,            // {customerId, admin, name, discountRate, addresses, cartCount}
  products: [],             // every Product (paintings and frames)
  byId: new Map(),
  listeners: [],
};

export const ACCOUNTS = [
  { id: "C001", name: "Nguyen Minh An", role: "VIP member · 10% off" },
  { id: "C002", name: "Tran Thu Binh", role: "New member" },
  { id: "ADMIN", name: "Gallery staff", role: "Back office" },
];

export function onSession(listener) {
  state.listeners.push(listener);
}

export async function refreshSession() {
  state.session = await api("/api/session");
  state.listeners.forEach((listener) => listener(state.session));
  return state.session;
}

export async function login(accountId) {
  await api("/api/login", { method: "POST", body: { customerId: accountId } });
  return refreshSession();
}

export async function loadProducts(force = false) {
  if (state.products.length && !force) return state.products;
  const results = await api("/api/products");
  state.products = results.map((result) => result.product);
  state.byId = new Map(state.products.map((product) => [product.productId, product]));
  return state.products;
}

let credits = null;
/** Credit, licence and Commons page of each painting image (/img/credits.json, written by the backend). */
export async function loadCredits() {
  if (!credits) credits = await fetch("/img/credits.json").then((r) => r.json()).catch(() => ({}));
  return credits;
}

export const paintings = () => state.products.filter((product) => product.category === "PAINTING");
export const frames = () => state.products.filter((product) => product.category === "FRAME");

// -------------------------------------------------------------- formatting

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function money(value) {
  const amount = Number(value || 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD",
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2, maximumFractionDigits: 2,
  }).format(amount);
}

export const cap = (text) => (text ? text.charAt(0).toUpperCase() + text.slice(1) : "");

export function date(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

let toastTimer;
export function toast(message, isError = false) {
  const element = document.getElementById("toast");
  element.textContent = message;
  element.classList.toggle("error", isError);
  element.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove("show"), 3600);
}

// --------------------------------------------------------- developer mode
// Shoppers never see scores, model names or tool calls. Developers (report, Q&A) turn on an overlay with
// ?debug=1 in the address or Shift + D; it shows the A06 score breakdown, the AI mode and the tools used.

export const developer = {
  on: /[?&]debug=1/.test(location.search + location.hash),   // never remembered, so shoppers never see it
  last: {},   // facts about the last request, shown in the developer panel
};

export function setDeveloper(on) {
  developer.on = on;
  document.body.classList.toggle("debug", on);
  renderDeveloperPanel();
}

/** Records facts about a request for the developer panel (no effect on what shoppers see). */
export function note(facts) {
  developer.last = { ...facts, at: new Date().toLocaleTimeString("en-GB") };
  renderDeveloperPanel();
}

function renderDeveloperPanel() {
  let panel = document.getElementById("dev-panel");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "dev-panel";
    panel.className = "dev-panel dev";
    document.body.appendChild(panel);
  }
  const rows = Object.entries(developer.last).map(([key, value]) =>
    `<div><span>${esc(key)}</span><b>${esc(typeof value === "number" && !Number.isInteger(value) ? value.toFixed(3) : value)}</b></div>`).join("");
  panel.innerHTML = `<strong>Developer view</strong><small>Shift + D to hide</small>${rows || "<div><span>no request yet</span></div>"}`;
}

/** "gemma" when the result reasons say Gemma answered, otherwise the keyword fallback. */
export function aiState(results) {
  if (!results || !results.length) return "none";
  return results.some((result) => /gemma/i.test(result.reason || "")) ? "gemma" : "fallback";
}

export function aiBadge(mode) {
  if (mode === "gemma") return `<span class="badge dev-inline"><i></i>Gemma 4</span>`;
  if (mode === "fallback") return `<span class="badge fallback dev-inline"><i></i>Keyword fallback</span>`;
  return "";
}

const TECHNICAL = /^(gemma 4( vision)?|keyword rules|local colour reading|your choice)$|visual match/i;
const COLOURS = ["blue", "green", "yellow", "red", "orange", "brown", "white", "black", "purple", "pink"];

/** Turns the server's reason ("Gemma 4 ▪ landscape ▪ blue") into words for shoppers ("Matches your blue tones · Landscape"). */
export function humanReason(reason, product) {
  const parts = String(reason || "").split("▪").map((part) => part.trim()).filter((part) => part && !TECHNICAL.test(part));
  if (!parts.length) return /visual match/i.test(reason || "") ? "Close to your photo" : "";
  const colour = parts.find((part) => COLOURS.includes(part.toLowerCase()));
  const artist = parts.find((part) => part === product?.artist?.name);
  const rest = parts.filter((part) => part !== colour && part !== artist).map(cap);
  return [colour && `Matches your ${colour.toLowerCase()} tones`, artist && `By ${artist}`, ...rest]
    .filter(Boolean).slice(0, 3).join(" · ");
}

// ------------------------------------------------------------------ frames

/** Colour stops of each Frame product, keyed by its material (used by CSS and by the canvas export). */
const FRAME_STOPS = {
  oak: ["#d2ab73", "#a87c46", "#c99d63", "#9b7140"],
  walnut: ["#74492b", "#4a2b17", "#6d4426", "#3f2413"],
  aluminium: ["#2c2c2c", "#121212", "#1b1b1b", "#262626"],
  "gilded wood": ["#e7c46e", "#a9822f", "#f0d27f", "#8f6a25"],
  "painted pine": ["#f7f5ef", "#e9e6de", "#f1eee7", "#dedad0"],
};

export function frameStops(frame) {
  return frame ? FRAME_STOPS[frame.material] || ["#1a1a1a", "#1a1a1a"] : null;
}

export function frameLook(frame) {
  const stops = frameStops(frame);
  if (!stops) return "transparent";
  const parts = stops.map((colour, i) => `${colour} ${Math.round((i * 100) / (stops.length - 1))}%`);
  return `linear-gradient(135deg, ${parts.join(", ")})`;
}

/** A painting inside an optional frame and passe-partout; sizes are in pixels. */
export function framedHtml(product, frame, { framePx = 14, matPx = 0, width = "" } = {}) {
  const border = frame ? framePx : 0;
  const style = `padding:${border}px;background:${frameLook(frame)};${width ? `width:${width};` : ""}`;
  const mat = `padding:${matPx}px;background:${matPx ? "#f3f0e8" : "transparent"}`;
  return `<div class="framed" style="${style}"><div class="mat" style="${mat}">
    <img src="${esc(product.imageUrl)}" alt="${esc(product.name)}" draggable="false"></div></div>`;
}

// -------------------------------------------------------------- templates

export function artistLine(product) {
  if (product.category !== "PAINTING") return `${esc(cap(product.material))} ▪ ${esc(product.sizeLabel)}`;
  return `${esc(product.artist?.name)} ▪ ${esc(product.yearCreated)}`;
}

export function productCard(product, result) {
  const image = product.category === "PAINTING"
    ? `<img src="${esc(product.imageUrl)}" alt="${esc(product.name)}" loading="lazy">`
    : `<div class="frame-swatch" style="background:${frameLook(product)}"><div></div></div>`;
  const reason = result ? humanReason(result.reason, product) : "";
  const tags = product.category === "PAINTING"
    ? `${esc(cap(product.style))} · ${esc(cap(product.subject))}`
    : `${esc(cap(product.material))} frame · ${esc(product.sizeLabel)}`;
  return `<a class="card" href="#/painting/${esc(product.productId)}">
    <div class="art">${image}<span class="view">View ↗</span></div>
    <div class="card-body">
      <div><h3 class="card-title">${esc(product.name)}</h3>
        <div class="card-meta">${product.category === "PAINTING" ? `${esc(product.artist?.name)}, ${esc(product.yearCreated)}` : "Frame"}</div>
        <div class="card-reason${reason ? " match" : ""}">${reason ? esc(reason) : tags}</div></div>
      <div class="price">${money(product.price)}</div>
    </div>
    ${result ? scoreHtml(result) : ""}
  </a>`;
}

/** Developer overlay only — score breakdown of slide A06: S = alpha*Stext + beta*Simage + gamma*Sbusiness. */
export function scoreHtml(result) {
  const bar = (label, value) => `<span>${label}</span><div class="bar"><i style="width:${Math.round((value || 0) * 100)}%"></i></div>
    <span>${(value || 0).toFixed(2)}</span>`;
  return `<div class="dev dev-scores"><div class="scores">${bar("Stext", result.textScore)}${bar("Simage", result.imageScore)}${bar("Sbusiness", result.businessScore)}</div>
    <div class="score-total"><span class="label">S</span><span class="mono">${(result.score || 0).toFixed(3)}</span></div>
    <div class="reason">${esc(result.reason || "")}</div></div>`;
}

export const STATUS_STEPS = ["PLACED", "PROCESSING", "SHIPPED", "DELIVERED"];

export function timelineHtml(status) {
  const index = STATUS_STEPS.indexOf(status);
  const steps = STATUS_STEPS.map((step, i) =>
    `<div class="${i <= index ? "done" : ""} ${i === index ? "current" : ""}">${step.toLowerCase()}</div>`).join("");
  return `<div class="timeline ${status === "CANCELLED" ? "cancelled" : ""}">${steps}</div>`;
}

// -------------------------------------------------------------------- files

export function readAsDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Re-encodes any photo the browser can decode (HEIC on Safari, GIF, a huge PNG…) as a JPEG of at most
 * `maxSide` pixels, so phone photos and big files always fit the 5 MB API limit. EXIF data (such as the
 * location) is dropped on the way. Rejects when the browser cannot read the file.
 */
export async function toJpeg(file, maxSide = 1600, quality = 0.85) {
  const url = URL.createObjectURL(file);
  try {
    const source = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("unreadable"));
      img.src = url;
    });
    if (source.naturalWidth < 16 || source.naturalHeight < 16) throw new Error("unreadable");
    const scale = Math.min(1, maxSide / Math.max(source.naturalWidth, source.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(source.naturalWidth * scale);
    canvas.height = Math.round(source.naturalHeight * scale);
    const context = canvas.getContext("2d");
    context.fillStyle = "#ffffff";   // transparent PNG areas become white, not black
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
    if (!blob) throw new Error("unreadable");
    const name = `${(file.name || "photo").replace(/\.[^.]+$/, "")}.jpg`;
    const jpeg = new File([blob], name, { type: "image/jpeg" });
    const dataUrl = await readAsDataUrl(jpeg);
    const image = new Image();
    image.src = dataUrl;
    await image.decode();
    return { file: jpeg, dataUrl, image };
  } finally {
    URL.revokeObjectURL(url);
  }
}

/**
 * Opens the device camera in a small window (live picture, "Take photo", "Cancel") and resolves with the photo as a
 * JPEG File, or with null when the customer cancels. A file input with `capture` only opens the camera on phones;
 * on a laptop the browser shows a file picker instead, so the camera is opened here with getUserMedia (allowed on
 * localhost). Rejects when the browser has no camera or the customer refuses access; the caller then falls back.
 */
export async function takePhoto(title = "Take a photo") {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("no camera");
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: "environment" }, width: { ideal: 1600 }, height: { ideal: 1200 } }, audio: false,
  });
  return new Promise((resolve) => {
    const box = document.createElement("div");
    box.className = "camera";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", title);
    box.innerHTML = `<div class="camera-panel">
      <div class="camera-head"><span class="label">${esc(title)}</span></div>
      <video class="camera-video" autoplay playsinline muted></video>
      <div class="camera-actions">
        <button type="button" class="btn" data-camera="cancel">Cancel</button>
        <button type="button" class="btn solid" data-camera="shoot">Take photo</button>
      </div>
    </div>`;
    document.body.appendChild(box);
    const video = box.querySelector("video");
    video.srcObject = stream;
    // A laptop camera faces the customer: show it like a mirror; the photo itself is not mirrored.
    if (stream.getVideoTracks()[0]?.getSettings().facingMode !== "environment") video.classList.add("mirror");
    const onKey = (event) => { if (event.key === "Escape") close(null); };
    function close(file) {
      stream.getTracks().forEach((track) => track.stop());
      document.removeEventListener("keydown", onKey);
      box.remove();
      resolve(file);
    }
    document.addEventListener("keydown", onKey);
    box.onclick = (event) => { if (event.target === box) close(null); };
    box.querySelector('[data-camera="cancel"]').onclick = () => close(null);
    const shoot = box.querySelector('[data-camera="shoot"]');
    shoot.onclick = () => {
      if (!video.videoWidth) return;                      // the first frame has not arrived yet
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d").drawImage(video, 0, 0);
      canvas.toBlob((blob) => close(blob && new File([blob], `photo-${Date.now()}.jpg`, { type: "image/jpeg" })),
        "image/jpeg", 0.92);
    };
    shoot.focus();
  });
}

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;   // same limit as the server (NFR03)

/** Adds one product to the signed-in customer's cart and refreshes the header count. */
export async function addToCart(productId, quantity = 1) {
  await api("/api/cart/items", { method: "POST", body: { productId, quantity } });
  await refreshSession();
}
