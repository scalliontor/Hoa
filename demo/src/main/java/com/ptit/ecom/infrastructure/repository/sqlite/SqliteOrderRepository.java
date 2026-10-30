package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.customer.Address;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderItem;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.order.Shipping;
import com.ptit.ecom.domain.order.ShippingStatus;
import com.ptit.ecom.domain.payment.PayCash;
import com.ptit.ecom.domain.payment.PayCredit;
import com.ptit.ecom.domain.payment.Payment;
import com.ptit.ecom.domain.payment.PaymentStatus;
import com.ptit.ecom.infrastructure.repository.OrderRepository;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * OrderRepository implemented with SQLite (slide A06: Order Database).
 * One order spans the rows of orders, order_item, shipping, payment and pay_cash / pay_credit.
 */
public class SqliteOrderRepository implements OrderRepository {
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private Database database;

    public SqliteOrderRepository(Database database) {
        this.database = database;
    }

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

    @Override
    public List<Order> findByCustomer(String customerId) {
        return findOrders("SELECT order_id FROM orders WHERE customer_id = ? ORDER BY order_date DESC", customerId);
    }

    @Override
    public List<Order> allOrders() {
        return findOrders("SELECT order_id FROM orders ORDER BY order_date DESC", null);
    }

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

    private List<Order> findOrders(String sql, String customerId) {
        List<String> ids = new ArrayList<>();
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            if (customerId != null) statement.setString(1, customerId);
            try (ResultSet rows = statement.executeQuery()) {
                while (rows.next()) ids.add(rows.getString("order_id"));
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read the order list", e);
        }
        List<Order> orders = new ArrayList<>();
        for (String id : ids) orders.add(findOrder(id));
        return orders;
    }

    private void loadItems(Connection connection, Order order) throws SQLException {
        SqliteProductRepository products = new SqliteProductRepository(database);
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT product_id, quantity, unit_price FROM order_item WHERE order_id = ? ORDER BY product_id")) {
            statement.setString(1, order.getOrderId());
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    OrderItem item = new OrderItem();
                    item.setProduct(products.findById(row.getString("product_id")));
                    item.setQuantity(row.getInt("quantity"));
                    item.setUnitPrice(row.getBigDecimal("unit_price"));
                    order.addItem(item);
                }
            }
        }
    }

    private void loadShipping(Connection connection, Order order) throws SQLException {
        String sql = "SELECT shipping_id, address_id, carrier, tracking_number, shipping_fee, status, delivered_date "
                + "FROM shipping WHERE order_id = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, order.getOrderId());
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) return;
                Shipping shipping = new Shipping();
                shipping.setShippingId(row.getString("shipping_id"));
                shipping.setCarrier(row.getString("carrier"));
                shipping.setTrackingNumber(row.getString("tracking_number"));
                shipping.setShippingFee(row.getBigDecimal("shipping_fee"));
                shipping.setStatus(ShippingStatus.valueOf(row.getString("status")));
                String delivered = row.getString("delivered_date");
                shipping.setDeliveredDate(delivered == null ? null : LocalDate.parse(delivered));
                shipping.setAddress(order.getCustomer().findAddress(row.getString("address_id")));
                order.setShipping(shipping);
            }
        }
    }

    private void loadPayments(Connection connection, Order order) throws SQLException {
        String sql = "SELECT payment_id, method, amount, payment_date, status FROM payment WHERE order_id = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, order.getOrderId());
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    String paymentId = row.getString("payment_id");
                    Payment payment = "CASH".equals(row.getString("method"))
                            ? loadCash(connection, paymentId) : loadCredit(connection, paymentId);
                    payment.setPaymentId(paymentId);
                    payment.setAmount(row.getBigDecimal("amount"));
                    String paidAt = row.getString("payment_date");
                    payment.setPaymentDate(paidAt == null ? null : LocalDateTime.parse(paidAt, TIME));
                    payment.setStatus(PaymentStatus.valueOf(row.getString("status")));
                    order.addPayment(payment);
                }
            }
        }
    }

    private PayCash loadCash(Connection connection, String paymentId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT cash_received, change_amount FROM pay_cash WHERE payment_id = ?")) {
            statement.setString(1, paymentId);
            try (ResultSet row = statement.executeQuery()) {
                PayCash cash = new PayCash();
                if (row.next()) {
                    cash.setCashReceived(row.getBigDecimal("cash_received"));
                    cash.setChangeAmount(row.getBigDecimal("change_amount"));
                }
                return cash;
            }
        }
    }

    private PayCredit loadCredit(Connection connection, String paymentId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT card_holder, bank_name, card_last4, authorization_code FROM pay_credit WHERE payment_id = ?")) {
            statement.setString(1, paymentId);
            try (ResultSet row = statement.executeQuery()) {
                PayCredit credit = new PayCredit();
                if (row.next()) {
                    credit.setCardHolder(row.getString("card_holder"));
                    credit.setBankName(row.getString("bank_name"));
                    credit.setCardLast4(row.getString("card_last4"));
                    credit.setAuthorizationCode(row.getString("authorization_code"));
                }
                return credit;
            }
        }
    }

    private void insertOrder(Connection connection, Order order) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO orders (order_id, customer_id, order_date, status, total_amount) VALUES (?, ?, ?, ?, ?)")) {
            statement.setString(1, order.getOrderId());
            statement.setString(2, order.getCustomer().getCustomerId());
            statement.setString(3, order.getOrderDate().format(TIME));
            statement.setString(4, order.getStatus().name());
            statement.setBigDecimal(5, order.getTotalAmount());
            statement.executeUpdate();
        }
    }

    private void insertItem(Connection connection, String orderId, OrderItem item) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)")) {
            statement.setString(1, orderId);
            statement.setString(2, item.getProduct().getProductId());
            statement.setInt(3, item.getQuantity());
            statement.setBigDecimal(4, item.getUnitPrice());
            statement.executeUpdate();
        }
    }

    private void insertShipping(Connection connection, Order order) throws SQLException {
        Shipping shipping = order.getShipping();
        String sql = "INSERT INTO shipping (shipping_id, order_id, address_id, carrier, tracking_number, shipping_fee, "
                + "status, delivered_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, shipping.getShippingId());
            statement.setString(2, order.getOrderId());
            statement.setString(3, shipping.getAddress().getAddressId());
            statement.setString(4, shipping.getCarrier());
            statement.setString(5, shipping.getTrackingNumber());
            statement.setBigDecimal(6, shipping.getShippingFee());
            statement.setString(7, shipping.getStatus().name());
            statement.setString(8, shipping.getDeliveredDate() == null ? null : shipping.getDeliveredDate().toString());
            statement.executeUpdate();
        }
    }

    private void insertPayment(Connection connection, String orderId, Payment payment) throws SQLException {
        String sql = "INSERT INTO payment (payment_id, order_id, method, amount, payment_date, status) "
                + "VALUES (?, ?, ?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, payment.getPaymentId());
            statement.setString(2, orderId);
            statement.setString(3, payment instanceof PayCash ? "CASH" : "CREDIT");
            statement.setBigDecimal(4, payment.getAmount());
            statement.setString(5, payment.getPaymentDate() == null ? null : payment.getPaymentDate().format(TIME));
            statement.setString(6, payment.getStatus().name());
            statement.executeUpdate();
        }
        if (payment instanceof PayCash) insertCash(connection, (PayCash) payment);
        else insertCredit(connection, (PayCredit) payment);
    }

    private void insertCash(Connection connection, PayCash cash) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO pay_cash (payment_id, cash_received, change_amount) VALUES (?, ?, ?)")) {
            statement.setString(1, cash.getPaymentId());
            statement.setBigDecimal(2, cash.getCashReceived());
            statement.setBigDecimal(3, cash.getChangeAmount());
            statement.executeUpdate();
        }
    }

    /** Only the last four card digits and the authorisation code are stored (NFR05). */
    private void insertCredit(Connection connection, PayCredit credit) throws SQLException {
        String sql = "INSERT INTO pay_credit (payment_id, card_holder, bank_name, card_last4, authorization_code) "
                + "VALUES (?, ?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, credit.getPaymentId());
            statement.setString(2, credit.getCardHolder());
            statement.setString(3, credit.getBankName());
            statement.setString(4, credit.getCardLast4());
            statement.setString(5, credit.getAuthorizationCode());
            statement.executeUpdate();
        }
    }

    private void updateShipping(Connection connection, String orderId, OrderStatus status) throws SQLException {
        boolean delivered = status == OrderStatus.DELIVERED;
        try (PreparedStatement statement = connection.prepareStatement(
                "UPDATE shipping SET status = ?, delivered_date = ? WHERE order_id = ?")) {
            statement.setString(1, delivered ? ShippingStatus.DELIVERED.name() : ShippingStatus.IN_TRANSIT.name());
            statement.setString(2, delivered ? LocalDate.now().toString() : null);
            statement.setString(3, orderId);
            statement.executeUpdate();
        }
    }
}
