// AdminView (model view): the operational use cases UC12 Manage Products and UC13 Update Order Status.
// Only an administrator session may call /api/admin; the order state rules live in Order.advanceTo.
import { api, date, esc, loadProducts, money, state, toast } from "./core.js";

const NEXT_STATUS = { PLACED: "PROCESSING", PROCESSING: "SHIPPED", SHIPPED: "DELIVERED" };

function productRow(product) {
  const thumb = product.category === "PAINTING" ? `<img src="${esc(product.imageUrl)}" alt="">` : "";
  return `<tr data-product="${esc(product.productId)}">
    <td><div class="thumb">${thumb}</div></td>
    <td><span class="mono">${esc(product.productId)}</span></td>
    <td>${esc(product.name)}<div class="card-meta">${product.category === "PAINTING" ? esc(product.artist?.name) : "Frame"}</div></td>
    <td><input class="input" type="number" min="0" step="1" data-field="price" value="${esc(product.price)}"></td>
    <td><input class="input" type="number" min="0" step="1" data-field="stock" value="${esc(product.stockQuantity)}"></td>
    <td><button type="button" class="btn small" data-save>Save</button></td>
  </tr>`;
}

function orderRow(order) {
  const next = NEXT_STATUS[order.status];
  const action = next
    ? `<button type="button" class="btn small" data-advance="${next}">Mark ${next.toLowerCase()}</button>`
    : `<span class="label">${order.status === "CANCELLED" ? "Cancelled by the customer" : "Completed"}</span>`;
  return `<tr data-order="${esc(order.orderId)}">
    <td><span class="mono">#${esc(order.orderId)}</span></td>
    <td>${esc(order.customer?.fullName ? `${order.customer.fullName.lastName} ${order.customer.fullName.middleName || ""} ${order.customer.fullName.firstName}`.replace(/\s+/g, " ") : order.customer?.customerId)}</td>
    <td>${date(order.orderDate)}</td>
    <td>${order.items.length}</td>
    <td>${money(order.totalAmount)}</td>
    <td><span class="status ${esc(order.status)}"><i></i>${esc(order.status.charAt(0) + order.status.slice(1).toLowerCase())}</span></td>
    <td>${action}</td>
  </tr>`;
}

/** Add-painting form handler (private): POST /api/admin/paintings -> AdminController.addPainting. */
async function addPainting(form) {
  const value = (name) => form.elements[name].value.trim();
  const body = {
    name: value("name"), artistId: value("artistId"), artistName: form.elements.artistId.selectedOptions[0].textContent,
    style: value("style"), subject: value("subject"), dominantColor: value("dominantColor"), medium: value("medium"),
    yearCreated: Number(value("yearCreated")), widthCm: Number(value("widthCm")), heightCm: Number(value("heightCm")),
    price: Number(value("price")), stockQuantity: Number(value("stockQuantity")), imageUrl: value("imageUrl"),
  };
  try {
    const painting = await api("/api/admin/paintings", { method: "POST", body });
    toast(`Added ${painting.name} (${painting.productId})`);
    await loadProducts(true);
    AdminView.renderProducts(await api("/api/admin/products"));
    form.reset();
  } catch (error) {
    toast(error.message, true);
  }
}

function addFormHtml() {
  const paintings = state.products.filter((p) => p.category === "PAINTING");
  const artists = [...new Map(paintings.map((p) => [p.artist.artistId, p.artist])).values()]
    .sort((a, b) => a.name.localeCompare(b.name));
  const images = paintings.map((p) => `<option value="${esc(p.imageUrl)}">${esc(p.imageUrl)}</option>`).join("");
  return `<form class="summary" id="add-painting" style="position:relative;top:0">
    <span class="label">Add a painting</span>
    <div class="form-grid" style="margin-top:16px">
      <div class="field wide"><label>Title</label><input class="input" name="name" required placeholder="Water Lilies"></div>
      <div class="field wide"><label>Artist</label><select class="input" name="artistId">${artists.map((a) => `<option value="${esc(a.artistId)}">${esc(a.name)}</option>`).join("")}</select></div>
      <div class="field"><label>Style</label><input class="input" name="style" required placeholder="Impressionism"></div>
      <div class="field"><label>Subject</label><input class="input" name="subject" required placeholder="landscape"></div>
      <div class="field"><label>Colour</label><input class="input" name="dominantColor" required placeholder="blue"></div>
      <div class="field"><label>Medium</label><input class="input" name="medium" required value="Canvas print"></div>
      <div class="field"><label>Year</label><input class="input" name="yearCreated" type="number" required value="1900"></div>
      <div class="field"><label>Price (USD)</label><input class="input" name="price" type="number" required value="89"></div>
      <div class="field"><label>Width cm</label><input class="input" name="widthCm" type="number" required value="50"></div>
      <div class="field"><label>Height cm</label><input class="input" name="heightCm" type="number" required value="70"></div>
      <div class="field"><label>Stock</label><input class="input" name="stockQuantity" type="number" required value="5"></div>
      <div class="field wide"><label>Image</label><select class="input" name="imageUrl">${images}</select></div>
    </div>
    <button type="submit" class="btn solid block" style="margin-top:18px">Add painting</button>
  </form>`;
}

export const AdminView = {
  /** Paintings and frames with editable price and stock, plus the add-painting form. */
  renderProducts(products) {
    const slot = document.getElementById("admin-body");
    if (!slot) return;
    slot.innerHTML = `<div class="admin-grid">
      <div class="table-wrap"><table class="table">
        <thead><tr><th></th><th>Id</th><th>Product</th><th>Price (USD)</th><th>Stock</th><th></th></tr></thead>
        <tbody>${products.map(productRow).join("")}</tbody></table></div>
      ${addFormHtml()}
    </div>`;
    slot.querySelectorAll("[data-save]").forEach((button) =>
      button.onclick = () => this.saveProduct(button.closest("tr").dataset.product));
    slot.querySelector("#add-painting").onsubmit = (event) => {
      event.preventDefault();
      addPainting(event.target);
    };
  },

  /** Saves the price and stock typed in one row (UC12). */
  async saveProduct(productId) {
    const row = document.querySelector(`tr[data-product="${productId}"]`);
    const price = Number(row.querySelector('[data-field="price"]').value);
    const stockQuantity = Number(row.querySelector('[data-field="stock"]').value);
    try {
      await api(`/api/admin/products/${productId}`, { method: "PUT", body: { price, stockQuantity } });
      toast(`Saved ${productId}: ${money(price)}, ${stockQuantity} in stock`);
      loadProducts(true);
    } catch (error) {
      toast(error.message, true);
    }
  },

  /** Every order with a button for the next allowed status (UC13). */
  renderOrders(orders) {
    const slot = document.getElementById("admin-body");
    if (!slot) return;
    const sorted = [...orders].sort((a, b) => String(b.orderDate).localeCompare(String(a.orderDate)));
    slot.innerHTML = `<div class="table-wrap"><table class="table">
      <thead><tr><th>Order</th><th>Customer</th><th>Date</th><th>Lines</th><th>Total</th><th>Status</th><th></th></tr></thead>
      <tbody>${sorted.map(orderRow).join("")}</tbody></table></div>
      <p class="label" style="margin-top:16px">Orders move one step at a time: placed → processing → shipped → delivered ▪ customers can cancel until an order ships</p>`;
    slot.querySelectorAll("[data-advance]").forEach((button) =>
      button.onclick = () => this.updateStatus(button.closest("tr").dataset.order, button.dataset.advance));
  },

  /** Moves one order to the next status; the server rejects any other move. */
  async updateStatus(orderId, status) {
    try {
      await api(`/api/admin/orders/${orderId}`, { method: "PUT", body: { status } });
      toast(`Order #${orderId} is now ${status.toLowerCase()}`);
      this.renderOrders(await api("/api/admin/orders"));
    } catch (error) {
      toast(error.message, true);
    }
  },
};
