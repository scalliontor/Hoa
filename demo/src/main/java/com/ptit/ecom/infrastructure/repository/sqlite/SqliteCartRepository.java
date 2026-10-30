package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.cart.CartItem;
import com.ptit.ecom.infrastructure.repository.CartRepository;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * CartRepository implemented with SQLite (slide A05: CartRepository).
 * Tables cart (at most one cart per customer, UNIQUE customer_id) and cart_item.
 */
public class SqliteCartRepository implements CartRepository {
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private Database database;

    public SqliteCartRepository(Database database) {
        this.database = database;
    }

    @Override
    public Cart findById(String cartId) {
        String sql = "SELECT cart_id, customer_id, created_date, updated_date FROM cart WHERE cart_id = ?";
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, cartId);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) return null;
                Cart cart = new Cart();
                cart.setCartId(cartId);
                cart.setCreatedDate(LocalDateTime.parse(row.getString("created_date"), TIME));
                cart.setUpdatedDate(LocalDateTime.parse(row.getString("updated_date"), TIME));
                cart.setOwner(new SqliteCustomerRepository(database).findById(row.getString("customer_id")));
                loadItems(connection, cart);
                return cart;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read cart " + cartId, e);
        }
    }

    /** A customer without a cart gets an empty one (association Customer 1 -- 0..1 Cart). */
    @Override
    public Cart findByCustomerId(String customerId) {
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT cart_id FROM cart WHERE customer_id = ?")) {
            statement.setString(1, customerId);
            try (ResultSet row = statement.executeQuery()) {
                if (row.next()) return findById(row.getString("cart_id"));
            }
            createCart(connection, "CART-" + customerId, customerId);
            return findById("CART-" + customerId);
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read the cart of customer " + customerId, e);
        }
    }

    /** Rewrites all cart lines in one transaction. */
    @Override
    public void save(Cart cart) {
        try (Connection connection = database.getConnection()) {
            connection.setAutoCommit(false);
            deleteItems(connection, cart.getCartId());
            for (CartItem item : cart.getItems()) insertItem(connection, cart.getCartId(), item);
            touch(connection, cart.getCartId());
            connection.commit();
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot save cart " + cart.getCartId(), e);
        }
    }

    @Override
    public void clear(String cartId) {
        try (Connection connection = database.getConnection()) {
            deleteItems(connection, cartId);
            touch(connection, cartId);
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot clear cart " + cartId, e);
        }
    }

    private void loadItems(Connection connection, Cart cart) throws SQLException {
        SqliteProductRepository products = new SqliteProductRepository(database);
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT product_id, quantity, cart_price FROM cart_item WHERE cart_id = ? ORDER BY product_id")) {
            statement.setString(1, cart.getCartId());
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    CartItem item = new CartItem(products.findById(row.getString("product_id")), row.getInt("quantity"));
                    item.setCartPrice(row.getBigDecimal("cart_price"));
                    cart.getItems().add(item);
                }
            }
        }
    }

    private void createCart(Connection connection, String cartId, String customerId) throws SQLException {
        String now = LocalDateTime.now().format(TIME);
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO cart (cart_id, customer_id, created_date, updated_date) VALUES (?, ?, ?, ?)")) {
            statement.setString(1, cartId);
            statement.setString(2, customerId);
            statement.setString(3, now);
            statement.setString(4, now);
            statement.executeUpdate();
        }
    }

    private void insertItem(Connection connection, String cartId, CartItem item) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO cart_item (cart_id, product_id, quantity, cart_price) VALUES (?, ?, ?, ?)")) {
            statement.setString(1, cartId);
            statement.setString(2, item.getProduct().getProductId());
            statement.setInt(3, item.getQuantity());
            statement.setBigDecimal(4, item.getCartPrice());
            statement.executeUpdate();
        }
    }

    private void deleteItems(Connection connection, String cartId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("DELETE FROM cart_item WHERE cart_id = ?")) {
            statement.setString(1, cartId);
            statement.executeUpdate();
        }
    }

    private void touch(Connection connection, String cartId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "UPDATE cart SET updated_date = ? WHERE cart_id = ?")) {
            statement.setString(1, LocalDateTime.now().format(TIME));
            statement.setString(2, cartId);
            statement.executeUpdate();
        }
    }
}
