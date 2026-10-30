package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.infrastructure.dao.OrderDAO;
import java.util.List;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class OrderService {
    private OrderDAO orderDAO;

    public OrderService(OrderDAO orderDAO) {
        this.orderDAO = orderDAO;
    }

    public Order getOrder(String customerId, String orderId) {
        Order order = orderDAO.findByIdAndCustomer(orderId, customerId);
        if (order == null) throw new IllegalArgumentException("Order not found: " + orderId);
        return order;
    }

    public List<Order> listOrders(String customerId) {
        return orderDAO.findByCustomer(customerId);
    }

    public void cancelOrder(String customerId, String orderId) {
        Order order = getOrder(customerId, orderId);
        order.cancel();
        orderDAO.updateStatus(orderId, order.getStatus());
    }
}
