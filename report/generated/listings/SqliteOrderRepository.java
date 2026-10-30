public class SqliteOrderRepository implements OrderRepository {
    // ...
    /** find_order(order_id) of slide A06; OrderService checks ownership. */
    @Override
    public Order findOrder(String orderId) {
        String sql = "SELECT order_id, customer_id, order_date, status, total_amount FROM orders WHERE order_id = ?";
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, orderId);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) return null;
                Order order = new Order();
                order.setOrderId(orderId);
                order.setOrderDate(LocalDateTime.parse(row.getString("order_date"), TIME));
                order.setStatus(OrderStatus.valueOf(row.getString("status")));
                order.setTotalAmount(row.getBigDecimal("total_amount"));
                order.setCustomer(new SqliteCustomerRepository(database).findById(row.getString("customer_id")));
                loadItems(connection, order);
                loadShipping(connection, order);
                loadPayments(connection, order);
                return order;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read order " + orderId, e);
        }
    }
    // ...
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
    // ...
}
