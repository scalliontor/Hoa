// SearchUI (model view, A06 "Search UI"): sends the customer's text, voice transcript or photo to the
// SearchController and passes the ranked results to SearchResultView. The UI never ranks anything itself.
import { aiState, api, esc, note, readAsDataUrl } from "./core.js";
import { SearchResultView } from "./search-result-view.js";

/** Shows a friendly loading line, runs the request and renders the results. */
async function run(kind, label, request) {
  const grid = document.getElementById("results");
  if (grid) {
    grid.className = "";
    grid.innerHTML = `<div class="loading"><span class="spinner"></span>Finding paintings ${esc(label)}…</div>`;
  }
  const started = performance.now();
  try {
    const results = await request();
    const seconds = (performance.now() - started) / 1000;
    SearchResultView.context = { label, seconds };
    note({ request: kind, ai: aiState(results), results: results.length, seconds,
      top: results[0] ? `${results[0].product.productId} ▪ S ${results[0].score.toFixed(3)}` : "none" });
    SearchResultView.render(results);
  } catch (error) {
    SearchResultView.context = { label, seconds: 0 };
    note({ request: kind, error: error.message });
    SearchResultView.renderEmpty("We couldn't search the collection just now. Please try again in a moment.");
  }
}

export const SearchUI = {
  /** Text search: Gemma 4 turns the sentence into filters (QueryService.textQuery). */
  submitText(text) {
    const query = (text || "").trim();
    if (!query) return run("text", "", () => api("/api/search?q="));
    history.replaceState(null, "", `#/collection?q=${encodeURIComponent(query)}`);
    return run("text", `for “${query}”`, () => api(`/api/search?q=${encodeURIComponent(query)}`));
  },

  /** Voice search: the Whisper transcript goes the same way as typed text (QueryService.voiceQuery). */
  submitVoice(transcript) {
    const query = (transcript || "").trim();
    if (!query) return SearchResultView.renderEmpty("We couldn't hear you — try typing.");
    return run("voice", `for “${query}”`, () => api("/api/search/voice", { method: "POST", body: { transcript: query } }));
  },

  /** Image search: Gemma 4 vision describes the photo, VectorIndex compares it by cosine similarity. */
  async submitImage(file) {
    if (!file) return;
    const image = await readAsDataUrl(file);
    return run("image", "like your photo", () => api("/api/search/image", { method: "POST", body: { image } }));
  },

  /** Text + image together (lambda_t = lambda_i = 0.5 in slide A06). */
  async submitMultimodal(text, file) {
    if (!file) return this.submitText(text);
    const image = await readAsDataUrl(file);
    return run("text + image", `for “${text}” like your photo`, () =>
      api("/api/search/multimodal", { method: "POST", body: { text, image } }));
  },
};
