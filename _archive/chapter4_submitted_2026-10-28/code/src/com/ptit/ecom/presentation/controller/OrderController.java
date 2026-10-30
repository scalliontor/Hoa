package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.domain.order.Order;
import java.util.List;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class OrderController {
    private OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    public Order viewOrder(String customerId, String orderId) {
        return orderService.getOrder(customerId, orderId);
    }

    public List<Order> listOrders(String customerId) {
        return orderService.listOrders(customerId);
    }

    public void cancelOrder(String customerId, String orderId) {
        orderService.cancelOrder(customerId, orderId);
    }
}
