// OrderView (model view): my orders with their status (FR08), look-up by id (FR09) and cancel before
// shipment (FR11). Ownership is decided on the server: another customer's order is refused (NFR01).
import { api, cap, date, esc, frameLook, money, refreshSession, timelineHtml, toast } from "./core.js";

function orderHtml(order) {
  const payment = order.payments?.[0] || {};
  const paid = payment.cardLast4 ? `Card •••• ${esc(payment.cardLast4)}` : "Cash on delivery";
  const status = cap(String(order.status || "").toLowerCase());
  const shipping = order.shipping || {};
  const address = shipping.address;
  const minis = order.items.map((item) => {
    const p = item.product;
    const inner = p.category === "PAINTING"
      ? `<img src="${esc(p.imageUrl)}" alt="${esc(p.name)}">`
      : `<div style="width:38px;height:48px;padding:5px;background:${frameLook(p)}"><div style="width:100%;height:100%;background:#2b3440"></div></div>`;
    return `<a class="mini" href="#/painting/${esc(p.productId)}" title="${esc(p.name)} × ${item.quantity}">${inner}</a>`;
  }).join("");
  const cancellable = order.status === "PLACED" || order.status === "PROCESSING";
  return `<article class="order" data-order="${esc(order.orderId)}">
    <div class="order-head">
      <div><span class="label">Order ▪ ${date(order.orderDate)}</span><h3>#${esc(order.orderId)}</h3></div>
      <span class="status ${esc(order.status)}"><i></i>${esc(status)}</span>
    </div>
    ${timelineHtml(order.status)}
    <div class="order-items">${minis}</div>
    <div class="row" style="justify-content:space-between;align-items:flex-end">
      <div class="stack" style="gap:4px">
        <span class="label">${esc(shipping.carrier || "Courier to be assigned")}${shipping.trackingNumber ? ` ▪ ${esc(shipping.trackingNumber)}` : ""}</span>
        <span class="muted">${address ? `${esc(address.houseNumber)} ${esc(address.street)}, ${esc(address.district)}, ${esc(address.city)}` : ""}</span>
        <span class="label">${paid}</span>
      </div>
      <div class="row">
        <span class="price" style="font-size:24px;font-weight:300">${money(order.totalAmount)}</span>
        ${cancellable ? `<button type="button" class="btn small" data-cancel>Cancel order</button>` : ""}
      </div>
    </div>
  </article>`;
}

/** The compact answer of a look-up, shown next to the list. */
function foundHtml(order) {
  const count = order.items.reduce((sum, item) => sum + item.quantity, 0);
  const shipping = order.shipping || {};
  return `<div class="found">
    <div class="row" style="justify-content:space-between"><strong>#${esc(order.orderId)}</strong>
      <span class="status ${esc(order.status)}"><i></i>${esc(cap(order.status.toLowerCase()))}</span></div>
    <span class="muted">${date(order.orderDate)} ▪ ${count} ${count === 1 ? "item" : "items"} ▪ ${money(order.totalAmount)}</span>
    ${shipping.trackingNumber ? `<span class="label">${esc(shipping.carrier)} ▪ ${esc(shipping.trackingNumber)}</span>` : ""}
    <button type="button" class="text-link" data-show style="justify-self:start">Show in my orders</button>
  </div>`;
}

function wireCancel(scope) {
  scope.querySelectorAll("[data-cancel]").forEach((button) => button.onclick = async () => {
    const orderId = button.closest("[data-order]").dataset.order;
    // First click arms the button, the second click within 5 seconds cancels the order.
    if (!button.dataset.armed) {
      button.dataset.armed = "1";
      button.textContent = "Confirm cancel";
      button.style.borderColor = "var(--err)";
      setTimeout(() => {
        delete button.dataset.armed;
        button.textContent = "Cancel order";
        button.style.borderColor = "";
      }, 5000);
      return;
    }
    try {
      await api(`/api/orders/${orderId}/cancel`, { method: "POST" });
      toast(`Order #${orderId} has been cancelled`);
      OrderView.render(await api("/api/orders"));
      refreshSession();
    } catch (error) {
      toast(error.message, true);
    }
  });
}

export const OrderView = {
  /** Renders the signed-in customer's orders, newest first. */
  render(orders) {
    const list = document.getElementById("order-list");
    if (!list) return;
    const sorted = [...(orders || [])].sort((a, b) => String(b.orderDate).localeCompare(String(a.orderDate)));
    list.innerHTML = sorted.length
      ? sorted.map(orderHtml).join("")
      : `<div class="empty"><p class="h3">No orders yet</p><p>Your orders will appear here after checkout.</p>
          <a class="btn" href="#/collection" style="margin-top:22px">Browse the collection</a></div>`;
    wireCancel(list);
  },

  /** Looks up one order by id; the server only answers for the owner. */
  async lookup(orderId) {
    const slot = document.getElementById("lookup-result");
    const id = (orderId || "").trim();
    if (!slot || !id) return;
    slot.innerHTML = `<div class="loading slim"><span class="spinner"></span>Looking for order #${esc(id)}…</div>`;
    try {
      const order = await api(`/api/orders/${encodeURIComponent(id)}`);
      slot.innerHTML = foundHtml(order);
      slot.querySelector("[data-show]").onclick = () => {
        const card = document.querySelector(`#order-list [data-order="${order.orderId}"]`);
        card?.scrollIntoView({ behavior: "smooth", block: "center" });
        card?.classList.add("flash");
        setTimeout(() => card?.classList.remove("flash"), 1600);
      };
    } catch (error) {
      slot.innerHTML = `<div class="notice error stacked">
        <strong>We can't show order #${esc(id)}</strong>
        <span class="muted">${esc(error.message)}. For your privacy, you can only see orders placed with your own account.</span>
      </div>`;
    }
  },
};
