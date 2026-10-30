package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.infrastructure.repository.CartRepository;

/**
 * CartRepository implemented with SQLite (slide A05).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class SqliteCartRepository implements CartRepository {
    private Database database;

    public SqliteCartRepository(Database database) {
        throw new UnsupportedOperationException("TODO: SqliteCartRepository");
    }

    @Override
    public Cart findById(String cartId) {
        throw new UnsupportedOperationException("TODO: findById");
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
        throw new UnsupportedOperationException("TODO: clear");
    }
}
