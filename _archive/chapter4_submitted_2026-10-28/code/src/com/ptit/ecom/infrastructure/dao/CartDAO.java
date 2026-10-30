package com.ptit.ecom.infrastructure.dao;

import com.ptit.ecom.domain.cart.Cart;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public interface CartDAO {
    Cart findByCustomerId(String customerId);

    void save(Cart cart);

    void clear(String cartId);
}
