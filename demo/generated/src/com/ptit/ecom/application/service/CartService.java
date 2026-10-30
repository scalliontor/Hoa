package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.infrastructure.repository.CartRepository;
import com.ptit.ecom.infrastructure.repository.ProductRepository;

/**
 * Application service that manages the cart (slide A05: Application Service).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class CartService {
    private CartRepository cartRepository;
    private ProductRepository productRepository;

    public CartService(CartRepository cartRepository, ProductRepository productRepository) {
        throw new UnsupportedOperationException("TODO: CartService");
    }

    public Cart addToCart(String customerId, String productId, int quantity) {
        throw new UnsupportedOperationException("TODO: addToCart");
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
