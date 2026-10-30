package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.freshDatabase;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.fails;
import static com.ptit.ecom.test.TestRunner.money;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.ptit.ecom.application.service.CartService;
import com.ptit.ecom.application.service.CheckoutService;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.order.ShippingStatus;
import com.ptit.ecom.domain.payment.PayCash;
import com.ptit.ecom.domain.payment.PayCredit;
import com.ptit.ecom.domain.payment.PaymentStatus;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.sqlite.Database;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteCartRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteCustomerRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteOrderRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteProductRepository;
import java.math.BigDecimal;

/** CheckoutService.checkout(cartId, customerId, ...) of slide A05 on the seeded database. */
final class CheckoutTest {
    private Database database;
    private SqliteProductRepository products;
    private SqliteCartRepository carts;
    private SqliteOrderRepository orders;
    private CheckoutService checkout;

    private CheckoutTest() throws Exception {
        database = freshDatabase();
        products = new SqliteProductRepository(database);
        carts = new SqliteCartRepository(database);
        orders = new SqliteOrderRepository(database);
        checkout = new CheckoutService(carts, orders, products, new SqliteCustomerRepository(database));
    }

    static void run() {
        test("Checkout saves the order, decreases stock and empties the cart", () -> {
            CheckoutTest t = new CheckoutTest();
            new CartService(t.carts, t.products).addToCart("C001", "F03", 1);
            Order order = t.checkout.checkout("CART-C001", "C001", "A001", new PayCash());
            same(OrderStatus.PLACED, order.getStatus(), "status");
            money("119.6", order.getTotalAmount(), "total: (89 + 35) - 10% VIP + 8 shipping");
            Order saved = t.orders.findOrder(order.getOrderId());
            same(2, saved.getItems().size(), "saved items");
            same(ShippingStatus.PREPARING, saved.getShipping().getStatus(), "shipping");
            same("A001", saved.getShipping().getAddress().getAddressId(), "address");
            same(PaymentStatus.PENDING, saved.getPayments().get(0).getStatus(), "cash is paid on delivery");
            same(4, t.products.findById("P03").getStockQuantity(), "stock of P03 (5 - 1)");
            check(t.carts.findById("CART-C001").isEmpty(), "cart emptied");
        });
        test("The price is read again from the catalogue at checkout", () -> {
            CheckoutTest t = new CheckoutTest();
            Product p03 = t.products.findById("P03");
            p03.setPrice(new BigDecimal("99"));
            t.products.save(p03);
            Order order = t.checkout.checkout("CART-C001", "C001", "A001", new PayCash());
            money("99", order.getItems().get(0).getUnitPrice(), "unit price (cart said 89)");
        });
        test("A customer cannot check out another customer's cart (NFR01)", () -> {
            CheckoutTest t = new CheckoutTest();
            fails(IllegalArgumentException.class, () -> t.checkout.checkout("CART-C001", "C002", "A003", new PayCash()));
            same(1, t.orders.findByCustomer("C002").size(), "orders of C002 unchanged");
            same(1, t.carts.findById("CART-C001").getItems().size(), "cart of C001 untouched");
        });
        test("An empty cart cannot be checked out", () -> {
            CheckoutTest t = new CheckoutTest();
            IllegalStateException error = fails(IllegalStateException.class,
                    () -> t.checkout.checkout("CART-C002", "C002", "A003", new PayCash()));
            same("Your cart is empty", error.getMessage(), "message");
        });
        test("A product sold out since it was added to the cart stops the checkout", () -> {
            CheckoutTest t = new CheckoutTest();
            Product p03 = t.products.findById("P03");
            p03.setStockQuantity(0);
            t.products.save(p03);
            fails(IllegalStateException.class, () -> t.checkout.checkout("CART-C001", "C001", "A001", new PayCash()));
            same(2, t.orders.findByCustomer("C001").size(), "no new order");
            same(1, t.carts.findById("CART-C001").getItems().size(), "cart kept");
        });
        test("A card is authorised (PayCredit.process); a declined card saves nothing", () -> {
            CheckoutTest t = new CheckoutTest();
            PayCredit declined = new PayCredit();
            declined.setCardLast4("4242");
            fails(IllegalStateException.class, () -> t.checkout.checkout("CART-C001", "C001", "A001", declined));
            same(2, t.orders.findByCustomer("C001").size(), "no order after a declined card");
            PayCredit card = new PayCredit();
            card.setCardHolder("Nguyen Minh An");
            card.setBankName("Demo card");
            card.setCardLast4("4242");
            card.setAuthorizationCode("SIM-1234");
            Order order = t.checkout.checkout("CART-C001", "C001", "A002", card);
            same(PaymentStatus.SUCCEEDED, order.getPayments().get(0).getStatus(), "card payment");
        });
        test("An address of another customer is refused", () -> {
            CheckoutTest t = new CheckoutTest();
            fails(IllegalArgumentException.class, () -> t.checkout.checkout("CART-C001", "C001", "A003", new PayCash()));
        });
    }
}
