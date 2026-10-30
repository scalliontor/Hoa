package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.CartService;
import com.ptit.ecom.domain.cart.Cart;

/**
 * Cart controller (slide A05).
 * customerId is taken from the session by the WebServer, never from the request body (NFR01).
 */
public class CartController {
    private CartService cartService;

    public CartController(CartService cartService) {
        this.cartService = cartService;
    }

    public Cart addItem(String customerId, String productId, int quantity) {
        return cartService.addToCart(customerId, productId, quantity);
    }

    public Cart updateQuantity(String customerId, String productId, int quantity) {
        return cartService.updateQuantity(customerId, productId, quantity);
    }

    public Cart removeItem(String customerId, String productId) {
        return cartService.removeItem(customerId, productId);
    }

    public Cart viewCart(String customerId) {
        return cartService.viewCart(customerId);
    }
}
