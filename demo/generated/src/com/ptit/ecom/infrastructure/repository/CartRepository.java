package com.ptit.ecom.infrastructure.repository;

import com.ptit.ecom.domain.cart.Cart;

/**
 * Cart repository (slide A05: CartRepository).
 * Generated from the 4.4 design model (tools/model.py).
 */
public interface CartRepository {
    Cart findById(String cartId);

    Cart findByCustomerId(String customerId);

    void save(Cart cart);

    void clear(String cartId);
}
