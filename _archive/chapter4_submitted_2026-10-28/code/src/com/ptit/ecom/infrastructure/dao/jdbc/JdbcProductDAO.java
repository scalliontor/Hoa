package com.ptit.ecom.infrastructure.dao.jdbc;

import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.dao.ProductDAO;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.List;
import javax.sql.DataSource;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class JdbcProductDAO implements ProductDAO {
    private DataSource dataSource;

    public JdbcProductDAO(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Product findById(String productId) {
        throw new UnsupportedOperationException("TODO: findById");
    }

    @Override
    public List<Product> searchByKeyword(String keyword, int limit) {
        throw new UnsupportedOperationException("TODO: searchByKeyword");
    }

    @Override
    public void decreaseStock(String productId, int quantity) {
        String sql = "UPDATE product SET stock_quantity = stock_quantity - ? "
                + "WHERE product_id = ? AND stock_quantity >= ?";
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setInt(1, quantity);
            statement.setString(2, productId);
            statement.setInt(3, quantity);
            if (statement.executeUpdate() != 1) throw new IllegalStateException("Not enough stock for " + productId);
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot update stock of " + productId, e);
        }
    }
}
