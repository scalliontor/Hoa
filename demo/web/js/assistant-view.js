// AssistantView (model view): the shopping assistant chat. Gemma 4 decides which tool to call (search paintings,
// find an order, latest order, list orders); AssistantService runs the tool for the signed-in customer only.
// Shoppers see only the answer; the tools and the AI mode are shown in the developer view.
import { api, esc, note } from "./core.js";

const TOOL_LABELS = {
  search_paintings: "Searched the collection",
  find_order: "Looked up an order",
  latest_order: "Checked your latest order",
  list_orders: "Listed your orders",
};

function chat() {
  return document.getElementById("chat");
}

function append(html) {
  const box = chat();
  box.insertAdjacentHTML("beforeend", html);
  box.scrollTop = box.scrollHeight;
  return box.lastElementChild;
}

/** Escapes the answer (line breaks are kept by CSS) and links order numbers to the order page. */
function answerHtml(text) {
  return esc(text.trim())
    .replace(/#?\b(2\d{7,13})\b/g, (match, id) => `<a href="#/orders?lookup=${id}">${match}</a>`);
}

export const AssistantView = {
  busy: false,

  /** Shows the customer's message, asks the server and renders the reply. */
  async send(message) {
    const text = (message || "").trim();
    if (!text || this.busy) return;
    this.busy = true;
    append(`<div class="msg user">${esc(text)}</div>`);
    const typing = append(`<div class="msg bot"><div class="bubble typing"><i></i><i></i><i></i></div></div>`);
    try {
      const reply = await api("/api/assistant", { method: "POST", body: { message: text } });
      typing.remove();
      this.render(reply);
    } catch (error) {
      typing.remove();
      note({ request: "assistant", error: error.message });
      this.render({ answer: "Sorry — I can't answer right now. Please try again in a moment.", toolsUsed: [], aiUsed: false });
    } finally {
      this.busy = false;
    }
  },

  /** Renders one AssistantReply: the answer for the shopper; the tools and AI mode for the developer view. */
  render(reply) {
    const answer = String(reply.answer || "").replace(/^\(Gemma 4 is offline\)\s*/i, "");
    const tools = (reply.toolsUsed || []).map((tool) =>
      `<span title="${esc(TOOL_LABELS[tool] || tool)}">Tool ▪ ${esc(tool)}</span>`).join("");
    append(`<div class="msg bot">
      <div class="bubble">${answerHtml(answer)}</div>
      <div class="dev"><div class="tools"><span>${reply.aiUsed ? "Gemma 4" : "Fallback ▪ no AI"}</span>${tools}</div></div>
    </div>`);
    note({ request: "assistant", ai: reply.aiUsed ? "gemma" : "fallback", tools: (reply.toolsUsed || []).join(", ") || "none" });
  },
};
