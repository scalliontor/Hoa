package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.freshDatabase;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.fails;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.order.ShippingStatus;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteOrderRepository;
import java.time.LocalDate;
import java.util.NoSuchElementException;

/** OrderService: "find my order", "my latest order", cancel (UC11) and status updates (UC13). */
final class OrderServiceTest {
    private OrderServiceTest() {
    }

    static void run() {
        test("find my order 20261001 returns the customer's own order", () -> {
            Order order = service().getOrder("C001", "20261001");
            same(OrderStatus.SHIPPED, order.getStatus(), "status");
        });
        test("Another customer's order is answered exactly like a missing one (NFR01)", () -> {
            OrderService orders = service();
            String other = fails(NoSuchElementException.class, () -> orders.getOrder("C001", "20261003")).getMessage();
            String missing = fails(NoSuchElementException.class, () -> orders.getOrder("C001", "20269999")).getMessage();
            same(missing.replace("20269999", "#"), other.replace("20261003", "#"), "same message");
            check(!other.contains("C002") && !other.contains("Tran"), "no data about the other customer");
        });
        test("where is my latest order? returns the newest order", () -> {
            same("20261001", service().latestOrder("C001").getOrderId(), "latest of C001");
            same("20261003", service().latestOrder("C002").getOrderId(), "latest of C002");
        });
        test("cancelOrder: only the owner, only PLACED or PROCESSING (UC11)", () -> {
            OrderService orders = service();
            fails(NoSuchElementException.class, () -> orders.cancelOrder("C001", "20261003"));
            fails(IllegalStateException.class, () -> orders.cancelOrder("C001", "20261001"));
            orders.cancelOrder("C002", "20261003");
            same(OrderStatus.CANCELLED, orders.getOrder("C002", "20261003").getStatus(), "saved status");
        });
        test("updateStatus moves one step and updates the shipping (UC13)", () -> {
            OrderService orders = service();
            fails(IllegalStateException.class, () -> orders.updateStatus("20261003", OrderStatus.DELIVERED));
            orders.updateStatus("20261003", OrderStatus.PROCESSING);
            Order shipped = orders.updateStatus("20261003", OrderStatus.SHIPPED);
            same(ShippingStatus.IN_TRANSIT, shipped.getShipping().getStatus(), "shipping when shipped");
            Order delivered = orders.updateStatus("20261003", OrderStatus.DELIVERED);
            same(ShippingStatus.DELIVERED, delivered.getShipping().getStatus(), "shipping when delivered");
            same(LocalDate.now(), delivered.getShipping().getDeliveredDate(), "delivered date");
            same(3, orders.listAllOrders().size(), "the administrator sees the 3 seeded orders");
        });
    }

    private static OrderService service() throws Exception {
        return new OrderService(new SqliteOrderRepository(freshDatabase()));
    }
}
