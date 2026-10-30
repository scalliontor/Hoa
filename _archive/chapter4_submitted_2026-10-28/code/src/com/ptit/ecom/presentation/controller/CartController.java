package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.CartService;
import com.ptit.ecom.domain.cart.Cart;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class CartController {
    private CartService cartService;

    public CartController(CartService cartService) {
        this.cartService = cartService;
    }

    public Cart addItem(String customerId, String productId, int quantity) {
        return cartService.addToCart(customerId, productId, quantity);
    }

    public Cart viewCart(String customerId) {
        return cartService.viewCart(customerId);
    }
}
