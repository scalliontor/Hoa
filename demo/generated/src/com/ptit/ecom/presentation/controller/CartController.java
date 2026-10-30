package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.CartService;
import com.ptit.ecom.domain.cart.Cart;

/**
 * Cart controller (slide A05).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class CartController {
    private CartService cartService;

    public CartController(CartService cartService) {
        throw new UnsupportedOperationException("TODO: CartController");
    }

    public Cart addItem(String customerId, String productId, int quantity) {
        throw new UnsupportedOperationException("TODO: addItem");
    }

    public Cart updateQuantity(String customerId, String productId, int quantity) {
        throw new UnsupportedOperationException("TODO: updateQuantity");
    }

    public Cart removeItem(String customerId, String productId) {
        throw new UnsupportedOperationException("TODO: removeItem");
    }

    public Cart viewCart(String customerId) {
        throw new UnsupportedOperationException("TODO: viewCart");
    }
}
