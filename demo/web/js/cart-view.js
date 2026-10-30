// CartView (model view): the cart lines (CartItem) and the checkout panel. Checkout itself happens on the
// server — CheckoutController -> CheckoutService.checkout(cartId, customerId, addressId, payment) (slide A05).
import { api, artistLine, esc, frameLook, money, refreshSession, state, timelineHtml, toast } from "./core.js";

const SHIPPING_FEE = 8;   // flat fee used by CheckoutService

function lineHtml(item) {
  const product = item.product;
  const thumb = product.category === "PAINTING"
    ? `<img src="${esc(product.imageUrl)}" alt="">`
    : `<div style="width:56px;height:72px;padding:7px;background:${frameLook(product)}"><div style="width:100%;height:100%;background:#2b3440"></div></div>`;
  return `<div class="line" data-product="${esc(product.productId)}">
    <a class="thumb" href="#/painting/${esc(product.productId)}">${thumb}</a>
    <div>
      <h3>${esc(product.name)}</h3>
      <div class="card-meta">${artistLine(product)}</div>
      <div class="row" style="margin-top:12px">
        <div class="qty"><button type="button" data-step="-1" aria-label="Decrease">−</button><span>${item.quantity}</span><button type="button" data-step="1" aria-label="Increase">+</button></div>
        <button type="button" class="link" data-remove>Remove</button>
      </div>
    </div>
    <div class="price">${money(item.cartPrice * item.quantity)}</div>
  </div>`;
}

function summaryHtml(cart) {
  const session = state.session || {};
  const subtotal = cart.items.reduce((sum, item) => sum + Number(item.cartPrice) * item.quantity, 0);
  const rate = Number(session.discountRate || 0);
  const discount = subtotal * rate;
  const addresses = (session.addresses || []).map((address, i) => `
    <label class="option ${i === 0 ? "selected" : ""}">
      <input type="radio" name="address" value="${esc(address.addressId)}" ${i === 0 ? "checked" : ""}>
      <span><strong style="font-weight:500">${esc(address.houseNumber)} ${esc(address.street)}</strong><br>
      <span class="muted">${esc(address.district)}, ${esc(address.city)}</span></span>
    </label>`).join("");
  return `<aside class="summary" id="checkout">
    <span class="label">Order summary</span>
    <div style="margin-top:14px">
      <div class="summary-row"><span>Subtotal</span><span>${money(subtotal)}</span></div>
      ${rate ? `<div class="summary-row"><span>VIP discount (${Math.round(rate * 100)}%)</span><span>−${money(discount)}</span></div>` : ""}
      <div class="summary-row"><span>Shipping</span><span>${money(SHIPPING_FEE)}</span></div>
      <div class="summary-total"><span class="label">Total</span><strong>${money(subtotal - discount + SHIPPING_FEE)}</strong></div>
    </div>
    <div class="divider"></div>
    <div class="stack">
      <span class="label">Deliver to</span>
      ${addresses || '<p class="muted">No address on file.</p>'}
    </div>
    <div class="divider"></div>
    <div class="stack">
      <span class="label">Payment</span>
      <label class="option selected"><input type="radio" name="payment" value="CASH" checked>
        <span>Cash on delivery<br><span class="muted">Pay the courier when the painting arrives.</span></span></label>
      <label class="option"><input type="radio" name="payment" value="CARD">
        <span>Card<br><span class="muted">Paid securely through our payment partner. We only keep the last four digits.</span></span></label>
      <div class="row hidden" id="card-fields">
        <input class="input" id="card-last4" inputmode="numeric" maxlength="4" placeholder="Last 4 digits" aria-label="Last four digits of the card" style="max-width:150px">
        <input class="input" id="card-holder" placeholder="Name on card" aria-label="Name on card" style="flex:1;min-width:160px">
      </div>
    </div>
    <button type="button" class="btn solid block" id="place-order" style="margin-top:22px">Place order</button>
    <p class="label" style="margin-top:12px;text-align:center">Prices are locked in when you place your order</p>
  </aside>`;
}

/** Wires quantity buttons, remove links and the checkout form after each render. */
function wire(container) {
  container.querySelectorAll(".line").forEach((line) => {
    const productId = line.dataset.product;
    const quantity = Number(line.querySelector(".qty span").textContent);
    line.querySelectorAll("[data-step]").forEach((button) => button.onclick = async () => {
      const next = quantity + Number(button.dataset.step);
      const cart = next <= 0
        ? await api(`/api/cart/items?productId=${productId}`, { method: "DELETE" })
        : await api("/api/cart/items", { method: "PUT", body: { productId, quantity: next } });
      CartView.render(cart);
      refreshSession();
    });
    line.querySelector("[data-remove]").onclick = async () => {
      CartView.render(await api(`/api/cart/items?productId=${productId}`, { method: "DELETE" }));
      refreshSession();
      toast("Removed from the cart");
    };
  });
  container.querySelectorAll(".option input").forEach((input) => input.onchange = () => {
    container.querySelectorAll(`input[name="${input.name}"]`).forEach((other) =>
      other.closest(".option").classList.toggle("selected", other.checked));
    if (input.name === "payment") container.querySelector("#card-fields").classList.toggle("hidden", input.value !== "CARD");
  });
  const place = container.querySelector("#place-order");
  if (place) place.onclick = () => CartView.checkout();
}

export const CartView = {
  /** Renders the cart lines and the checkout panel. */
  render(cart) {
    const container = document.getElementById("cart-view");
    if (!container) return;
    if (!cart.items || !cart.items.length) {
      container.innerHTML = `<div class="empty"><p class="h3">Your cart is empty</p>
        <p>Describe a painting, say it, or show us your room — we'll help you find it.</p>
        <a class="btn" href="#/collection" style="margin-top:22px">Browse the collection</a></div>`;
      return;
    }
    const count = cart.items.reduce((sum, item) => sum + item.quantity, 0);
    container.innerHTML = `<div class="cart">
      <div><div class="row" style="justify-content:space-between;margin-bottom:12px">
          <span class="label">${count} ${count === 1 ? "item" : "items"}</span>
          <a class="link" href="#/collection">Continue browsing</a></div>
        ${cart.items.map(lineHtml).join("")}</div>
      ${summaryHtml(cart)}
    </div>`;
    wire(container);
  },

  /** Sends the checkout to the server and shows the confirmation. */
  async checkout() {
    const container = document.getElementById("cart-view");
    const addressId = container.querySelector('input[name="address"]:checked')?.value;
    const method = container.querySelector('input[name="payment"]:checked')?.value || "CASH";
    let paymentMethod = "CASH";
    if (method === "CARD") {
      const last4 = container.querySelector("#card-last4").value.trim();
      if (!/^\d{4}$/.test(last4)) return toast("Please enter the last four digits of your card", true);
      paymentMethod = `CARD:${last4}:${container.querySelector("#card-holder").value.trim()}`;
    }
    const button = container.querySelector("#place-order");
    button.disabled = true;
    button.innerHTML = '<span class="spinner"></span> Placing order';
    try {
      const order = await api("/api/checkout", { method: "POST", body: { addressId, paymentMethod } });
      await refreshSession();
      container.innerHTML = confirmationHtml(order);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      toast(error.message, true);
      button.disabled = false;
      button.textContent = "Place order";
    }
  },
};

function confirmationHtml(order) {
  const payment = order.payments?.[0] || {};
  const paid = payment.cardLast4 ? `Card •••• ${esc(payment.cardLast4)} ▪ approved` : "Cash on delivery";
  const address = order.shipping?.address;
  const items = order.items.map((item) => `<div class="summary-row">
      <span>${esc(item.product.name)} × ${item.quantity}</span><span>${money(item.unitPrice * item.quantity)}</span></div>`).join("");
  return `<div class="confirm">
    <span class="label">Order placed</span>
    <h2 class="display" style="margin:14px 0 8px">Thank you.</h2>
    <p class="lead">Your order <strong style="color:var(--text);font-weight:500">#${esc(order.orderId)}</strong> is confirmed. You can follow it — or cancel it until it ships — in My orders.</p>
    ${timelineHtml(order.status)}
    <div class="summary" style="position:relative;top:0;margin-top:28px">
      ${items}
      <div class="summary-row"><span>Shipping</span><span>${money(order.shipping?.shippingFee || 0)}</span></div>
      <div class="summary-total"><span class="label">Total</span><strong>${money(order.totalAmount)}</strong></div>
      <div class="divider"></div>
      <div class="summary-row"><span class="label">Deliver to</span><span>${address ? `${esc(address.houseNumber)} ${esc(address.street)}, ${esc(address.city)}` : ""}</span></div>
      <div class="summary-row"><span class="label">Payment</span><span>${paid}</span></div>
    </div>
    <div class="row" style="margin-top:26px"><a class="btn solid" href="#/orders">View my orders</a><a class="btn" href="#/collection">Keep browsing</a></div>
  </div>`;
}
