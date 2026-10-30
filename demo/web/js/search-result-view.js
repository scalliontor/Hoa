// SearchResultView (model view, A06 "Search Result View"): shows the ranked results as painting cards with a
// short human reason. The score breakdown S = alpha*Stext + beta*Simage + gamma*Sbusiness and the AI mode
// are rendered too, but only the developer view (?debug=1 or Shift + D) makes them visible.
import { aiBadge, aiState, esc, productCard } from "./core.js";

const IDEAS = ["blue landscape paintings", "yellow flowers for a kitchen", "calm Japanese prints with water"];

export const SearchResultView = {
  results: [],
  filter: "ALL",                       // ALL, PAINTING or FRAME (chips above the grid)
  context: { label: "", seconds: 0 },  // set by SearchUI before render: what was asked and how long it took

  /** Renders a list of SearchResult objects. */
  render(results) {
    this.results = results || [];
    const grid = document.getElementById("results");
    if (!grid) return;
    const shown = this.results.filter((r) => this.filter === "ALL" || r.product.category === this.filter);
    renderMeta(this, shown.length);
    if (!shown.length) {
      this.renderEmpty("Try fewer words, another colour or artist — or browse everything.");
      return;
    }
    const asked = this.context.label !== "";
    grid.className = "grid-3";
    grid.innerHTML = shown.map((result) => productCard(result.product, asked ? result : null)).join("");
  },

  /** Empty state: a valid answer of the search, with a few ideas to try next. */
  renderEmpty(message) {
    const grid = document.getElementById("results");
    if (!grid) return;
    grid.className = "";
    grid.innerHTML = `<div class="empty"><p class="h3">No paintings found</p>
      <p>${esc(message)}</p>
      <div class="chips" style="justify-content:center;margin-top:22px">
        ${IDEAS.map((idea) => `<a class="chip" href="#/collection?q=${encodeURIComponent(idea)}">${esc(idea)}</a>`).join("")}
        <a class="chip" href="#/collection">Browse everything</a></div></div>`;
  },
};

/** Result count and the request above the grid (private helper); timing and AI mode are developer-only. */
function renderMeta(view, count) {
  const slot = document.getElementById("results-meta-text");
  if (!slot) return;
  const { label, seconds } = view.context;
  const noun = { ALL: "work", PAINTING: "painting", FRAME: "frame" }[view.filter];
  document.querySelector(".results-meta .filters")?.classList.remove("hidden");   // hidden while room picks are shown
  slot.innerHTML = `<span class="results-count">${count} ${noun}${count === 1 ? "" : "s"} ${esc(label)}</span>
    ${label ? `${aiBadge(aiState(view.results))}<span class="label dev-inline">${seconds.toFixed(2)} s</span>` : ""}`;
}
