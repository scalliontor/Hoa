package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.infrastructure.repository.OrderRepository;
import java.util.List;

/**
 * Order service: lookups check ownership (slide A05, NFR01).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class OrderService {
    private OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        throw new UnsupportedOperationException("TODO: OrderService");
    }

    public Order getOrder(String customerId, String orderId) {
        throw new UnsupportedOperationException("TODO: getOrder");
    }

    public List<Order> listOrders(String customerId) {
        throw new UnsupportedOperationException("TODO: listOrders");
    }

    public Order latestOrder(String customerId) {
        throw new UnsupportedOperationException("TODO: latestOrder");
    }

    public void cancelOrder(String customerId, String orderId) {
        throw new UnsupportedOperationException("TODO: cancelOrder");
    }

    public List<Order> listAllOrders() {
        throw new UnsupportedOperationException("TODO: listAllOrders");
    }

    public Order updateStatus(String orderId, OrderStatus status) {
        throw new UnsupportedOperationException("TODO: updateStatus");
    }
}
