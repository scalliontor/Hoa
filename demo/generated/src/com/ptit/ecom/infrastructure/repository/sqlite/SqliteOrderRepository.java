package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.infrastructure.repository.OrderRepository;
import java.util.List;

/**
 * OrderRepository implemented with SQLite (slide A06: Order Database).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class SqliteOrderRepository implements OrderRepository {
    private Database database;

    public SqliteOrderRepository(Database database) {
        throw new UnsupportedOperationException("TODO: SqliteOrderRepository");
    }

    @Override
    public Order findOrder(String orderId) {
        throw new UnsupportedOperationException("TODO: findOrder");
    }

    @Override
    public List<Order> findByCustomer(String customerId) {
        throw new UnsupportedOperationException("TODO: findByCustomer");
    }

    @Override
    public List<Order> allOrders() {
        throw new UnsupportedOperationException("TODO: allOrders");
    }

    @Override
    public void save(Order order) {
        throw new UnsupportedOperationException("TODO: save");
    }

    @Override
    public void updateStatus(String orderId, OrderStatus status) {
        throw new UnsupportedOperationException("TODO: updateStatus");
    }
}
