package com.ptit.ecom.infrastructure.dao;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import java.util.List;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public interface OrderDAO {
    void save(Order order);

    Order findByIdAndCustomer(String orderId, String customerId);

    List<Order> findByCustomer(String customerId);

    void updateStatus(String orderId, OrderStatus status);
}
