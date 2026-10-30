public class SqliteOrderRepository implements OrderRepository {
    // ... (other members omitted)
    /** Writes a new order with its lines, shipping and payments in one transaction. */
    @Override
    public void save(Order order) {
        try (Connection connection = database.getConnection()) {
            connection.setAutoCommit(false);
            insertOrder(connection, order);
            for (OrderItem item : order.getItems()) insertItem(connection, order.getOrderId(), item);
            if (order.getShipping() != null) insertShipping(connection, order);
            for (Payment payment : order.getPayments()) insertPayment(connection, order.getOrderId(), payment);
            connection.commit();
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot save order " + order.getOrderId(), e);
        }
    }

    /** The shipping state follows the order state: SHIPPED -> IN_TRANSIT, DELIVERED -> DELIVERED. */
    @Override
    public void updateStatus(String orderId, OrderStatus status) {
        try (Connection connection = database.getConnection()) {
            connection.setAutoCommit(false);
            try (PreparedStatement statement = connection.prepareStatement(
                    "UPDATE orders SET status = ? WHERE order_id = ?")) {
                statement.setString(1, status.name());
                statement.setString(2, orderId);
                statement.executeUpdate();
            }
            if (status == OrderStatus.SHIPPED || status == OrderStatus.DELIVERED) updateShipping(connection, orderId, status);
            connection.commit();
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot update order " + orderId, e);
        }
    }
}
