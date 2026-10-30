package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.domain.order.Order;
import java.util.List;

/**
 * Order controller (slide A05).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class OrderController {
    private OrderService orderService;

    public OrderController(OrderService orderService) {
        throw new UnsupportedOperationException("TODO: OrderController");
    }

    public Order viewOrder(String customerId, String orderId) {
        throw new UnsupportedOperationException("TODO: viewOrder");
    }

    public List<Order> listOrders(String customerId) {
        throw new UnsupportedOperationException("TODO: listOrders");
    }

    public void cancelOrder(String customerId, String orderId) {
        throw new UnsupportedOperationException("TODO: cancelOrder");
    }
}
