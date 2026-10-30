public interface OrderDAO {
    void save(Order order);
    Order findByIdAndCustomer(String orderId, String customerId);
    List<Order> findByCustomer(String customerId);
    void updateStatus(String orderId, OrderStatus status);
}

public class JdbcOrderDAO implements OrderDAO {
    // ... constructor and other methods omitted

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
}
