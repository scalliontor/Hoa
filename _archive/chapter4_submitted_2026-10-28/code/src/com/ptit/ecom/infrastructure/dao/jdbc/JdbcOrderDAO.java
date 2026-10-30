package com.ptit.ecom.infrastructure.dao.jdbc;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.infrastructure.dao.OrderDAO;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import javax.sql.DataSource;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class JdbcOrderDAO implements OrderDAO {
    private DataSource dataSource;

    public JdbcOrderDAO(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public void save(Order order) {
        throw new UnsupportedOperationException("TODO: save");
    }

    @Override
    public Order findByIdAndCustomer(String orderId, String customerId) {
        // The customer id comes from the authenticated session, never from the request body.
        String sql = "SELECT order_id, order_date, status, total_amount FROM orders "
                + "WHERE order_id = ? AND customer_id = ?";
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, orderId);
            statement.setString(2, customerId);
            try (ResultSet rows = statement.executeQuery()) {
                if (!rows.next()) return null;
                Order order = new Order();
                order.setOrderId(rows.getString("order_id"));
                order.setOrderDate(rows.getTimestamp("order_date").toLocalDateTime());
                order.setStatus(OrderStatus.valueOf(rows.getString("status")));
                order.setTotalAmount(rows.getBigDecimal("total_amount"));
                return order;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read order " + orderId, e);
        }
    }

    @Override
    public List<Order> findByCustomer(String customerId) {
        throw new UnsupportedOperationException("TODO: findByCustomer");
    }

    @Override
    public void updateStatus(String orderId, OrderStatus status) {
        throw new UnsupportedOperationException("TODO: updateStatus");
    }
}
