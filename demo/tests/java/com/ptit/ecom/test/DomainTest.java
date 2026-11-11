package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.category;
import static com.ptit.ecom.test.Fixtures.customer;
import static com.ptit.ecom.test.Fixtures.frame;
import static com.ptit.ecom.test.Fixtures.painting;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.fails;
import static com.ptit.ecom.test.TestRunner.money;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.cart.CartItem;
import com.ptit.ecom.domain.customer.CustomerNew;
import com.ptit.ecom.domain.customer.CustomerVIP;
import com.ptit.ecom.domain.customer.FullName;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderItem;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.order.Shipping;
import com.ptit.ecom.domain.payment.PayCash;
import com.ptit.ecom.domain.payment.PayCredit;
import com.ptit.ecom.domain.payment.PaymentStatus;
import com.ptit.ecom.domain.product.Category;
import com.ptit.ecom.domain.product.DetailKind;
import com.ptit.ecom.domain.product.Painting;
import java.math.BigDecimal;

/** Business rules of the domain classes (sections 4.1 and 4.3), without database or AI. */
final class DomainTest {
    private DomainTest() {
    }

    static void run() {
        test("FullName shows last, middle and first name", () -> {
            FullName name = new FullName();
            name.setFirstName("An");
            name.setMiddleName("Minh");
            name.setLastName("Nguyen");
            same("Nguyen Minh An", name.getDisplayName(), "display name");
            name.setMiddleName(null);
            same("Nguyen An", name.getDisplayName(), "display name without middle name");
        });
        test("Cart.addItem merges the same product and refuses quantity 0", () -> {
            Cart cart = new Cart();
            Painting monet = painting("P01", "79", 5);
            cart.addItem(monet, 1);
            cart.addItem(monet, 2);
            same(1, cart.getItems().size(), "lines");
            same(3, cart.getItems().get(0).getQuantity(), "quantity");
            fails(IllegalArgumentException.class, () -> cart.addItem(monet, 0));
        });
        test("Cart.calculateTotal sums the lines; updateQuantity(0) removes a line", () -> {
            Cart cart = new Cart();
            cart.addItem(painting("P01", "79", 5), 2);
            cart.addItem(frame("F03", "35"), 1);
            money("193", cart.calculateTotal(), "cart total");
            cart.updateQuantity("P01", 0);
            same(1, cart.getItems().size(), "lines left");
            money("35", cart.calculateTotal(), "cart total after removal");
        });
        test("OrderItem.fromCartItem takes the current catalogue price, not the cart price", () -> {
            CartItem line = new CartItem(painting("P01", "79", 5), 1);
            OrderItem item = OrderItem.fromCartItem(line, painting("P01", "99", 5));
            money("79", line.getCartPrice(), "cart price");
            money("99", item.getUnitPrice(), "unit price");
        });
        test("Order.calculateTotal: subtotal minus VIP discount plus shipping fee", () -> {
            Order order = new Order();
            order.addItem(OrderItem.fromCartItem(new CartItem(painting("P03", "89", 5), 1), painting("P03", "89", 5)));
            order.addItem(OrderItem.fromCartItem(new CartItem(frame("F03", "35"), 1), frame("F03", "35")));
            Shipping shipping = new Shipping();
            shipping.setShippingFee(new BigDecimal("8"));
            order.setShipping(shipping);
            money("119.6", order.calculateTotal(new BigDecimal("0.10")), "total (124 - 10% + 8)");
        });
        test("Order.cancel is allowed only before shipment (UC11)", () -> {
            Order placed = order(OrderStatus.PROCESSING);
            placed.cancel();
            same(OrderStatus.CANCELLED, placed.getStatus(), "status");
            fails(IllegalStateException.class, () -> order(OrderStatus.SHIPPED).cancel());
            fails(IllegalStateException.class, () -> order(OrderStatus.DELIVERED).cancel());
        });
        test("Order.advanceTo moves one step: PLACED > PROCESSING > SHIPPED > DELIVERED (UC13)", () -> {
            Order order = order(OrderStatus.PLACED);
            order.advanceTo(OrderStatus.PROCESSING);
            order.advanceTo(OrderStatus.SHIPPED);
            order.advanceTo(OrderStatus.DELIVERED);
            same(OrderStatus.DELIVERED, order.getStatus(), "status");
            fails(IllegalStateException.class, () -> order(OrderStatus.PLACED).advanceTo(OrderStatus.DELIVERED));
            fails(IllegalStateException.class, () -> order(OrderStatus.SHIPPED).advanceTo(OrderStatus.PLACED));
            fails(IllegalStateException.class, () -> order(OrderStatus.CANCELLED).advanceTo(OrderStatus.PROCESSING));
        });
        test("Order.isOwnedBy compares the customer id (NFR01)", () -> {
            Order order = order(OrderStatus.PLACED);
            check(order.isOwnedBy("C001"), "owner");
            check(!order.isOwnedBy("C002"), "other customer");
        });
        test("Product.decreaseStock never goes below zero", () -> {
            Painting painting = painting("P01", "79", 2);
            fails(IllegalStateException.class, () -> painting.decreaseStock(3));
            painting.decreaseStock(2);
            same(0, painting.getStockQuantity(), "stock");
            check(!painting.isAvailable(1), "sold out");
        });
        test("Category.accepts only products of its detail kind", () -> {
            Category frames = category("CAT-FRAMES", "Frames", DetailKind.FRAME);
            same(true, frames.accepts(frame("F03", "35")), "frame in Frames");
            same(false, frames.accepts(painting("P01", "79", 5)), "painting in Frames");
        });
        test("Payment.process is polymorphic: card needs an authorisation, cash needs enough money", () -> {
            PayCredit card = new PayCredit();
            card.setAmount(new BigDecimal("107"));
            check(!card.process(), "card without authorisation");
            same(PaymentStatus.FAILED, card.getStatus(), "card status");
            card.setAuthorizationCode("AUTH-7731");
            check(card.process(), "authorised card");
            same(PaymentStatus.SUCCEEDED, card.getStatus(), "card status");
            PayCash cash = new PayCash();
            cash.setAmount(new BigDecimal("100"));
            cash.setCashReceived(new BigDecimal("120"));
            check(cash.process(), "cash");
            money("20", cash.getChangeAmount(), "change");
        });
        test("Customer.findAddress refuses an address of another customer", () -> {
            fails(IllegalArgumentException.class, () -> customer("C001", "A001").findAddress("A003"));
            same("A001", customer("C001", "A001").findAddress("A001").getAddressId(), "own address");
        });
        test("Only a VIP customer has a discount", () -> {
            CustomerVIP vip = new CustomerVIP();
            vip.setDiscountRate(new BigDecimal("0.10"));
            money("0.10", vip.getDiscountRate(), "VIP discount");
            money("0", new CustomerNew().getDiscountRate(), "new customer discount");
        });
    }

    private static Order order(OrderStatus status) {
        Order order = new Order();
        order.setOrderId("20261099");
        order.setStatus(status);
        order.setCustomer(customer("C001", "A001"));
        return order;
    }
}
