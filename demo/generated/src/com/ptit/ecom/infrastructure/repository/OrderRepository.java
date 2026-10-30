package com.ptit.ecom.infrastructure.repository;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import java.util.List;

/**
 * Order repository, find_order() of slide A06 (slide A05: OrderRepository).
 * Generated from the 4.4 design model (tools/model.py).
 */
public interface OrderRepository {
    Order findOrder(String orderId);

    List<Order> findByCustomer(String customerId);

    List<Order> allOrders();

    void save(Order order);

    void updateStatus(String orderId, OrderStatus status);
}
