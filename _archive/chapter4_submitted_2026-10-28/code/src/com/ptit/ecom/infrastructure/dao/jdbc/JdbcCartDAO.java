package com.ptit.ecom.infrastructure.dao.jdbc;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.infrastructure.dao.CartDAO;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import javax.sql.DataSource;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class JdbcCartDAO implements CartDAO {
    private DataSource dataSource;

    public JdbcCartDAO(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Cart findByCustomerId(String customerId) {
        throw new UnsupportedOperationException("TODO: findByCustomerId");
    }

    @Override
    public void save(Cart cart) {
        throw new UnsupportedOperationException("TODO: save");
    }

    @Override
    public void clear(String cartId) {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement("DELETE FROM cart_item WHERE cart_id = ?")) {
            statement.setString(1, cartId);
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot clear cart " + cartId, e);
        }
    }
}
