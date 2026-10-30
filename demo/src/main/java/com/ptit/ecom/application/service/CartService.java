package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.CartRepository;
import com.ptit.ecom.infrastructure.repository.ProductRepository;

/**
 * Application service that manages the cart (slide A05: Application Service).
 * The rules live in Cart (addItem, updateQuantity); the service loads, calls and saves.
 */
public class CartService {
    private CartRepository cartRepository;
    private ProductRepository productRepository;

    public CartService(CartRepository cartRepository, ProductRepository productRepository) {
        this.cartRepository = cartRepository;
        this.productRepository = productRepository;
    }

    public Cart addToCart(String customerId, String productId, int quantity) {
        Product product = productRepository.findById(productId);
        if (product == null || !product.isAvailable(quantity)) {
            throw new IllegalArgumentException("This item is not available in that quantity: " + productId);
        }
        Cart cart = cartRepository.findByCustomerId(customerId);
        cart.addItem(product, quantity);
        cartRepository.save(cart);
        return cart;
    }

    public Cart updateQuantity(String customerId, String productId, int quantity) {
        Product product = productRepository.findById(productId);
        if (product != null && quantity > 0 && !product.isAvailable(quantity)) {
            throw new IllegalArgumentException("Only " + product.getStockQuantity() + " left of " + product.getName());
        }
        Cart cart = cartRepository.findByCustomerId(customerId);
        cart.updateQuantity(productId, quantity);
        cartRepository.save(cart);
        return cart;
    }

    public Cart removeItem(String customerId, String productId) {
        Cart cart = cartRepository.findByCustomerId(customerId);
        cart.removeItem(productId);
        cartRepository.save(cart);
        return cart;
    }

    public Cart viewCart(String customerId) {
        return cartRepository.findByCustomerId(customerId);
    }
}
