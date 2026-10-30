package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.ProductRepository;
import java.util.List;

/**
 * ProductRepository implemented with SQLite (slide A06: Product Database).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class SqliteProductRepository implements ProductRepository {
    private Database database;

    public SqliteProductRepository(Database database) {
        throw new UnsupportedOperationException("TODO: SqliteProductRepository");
    }

    @Override
    public List<Product> allProducts() {
        throw new UnsupportedOperationException("TODO: allProducts");
    }

    @Override
    public Product findById(String productId) {
        throw new UnsupportedOperationException("TODO: findById");
    }

    @Override
    public void decreaseStock(String productId, int quantity) {
        throw new UnsupportedOperationException("TODO: decreaseStock");
    }

    @Override
    public void save(Product product) {
        throw new UnsupportedOperationException("TODO: save");
    }
}
