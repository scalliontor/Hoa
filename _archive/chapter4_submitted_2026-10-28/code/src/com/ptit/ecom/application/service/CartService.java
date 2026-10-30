package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.dao.CartDAO;
import com.ptit.ecom.infrastructure.dao.ProductDAO;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class CartService {
    private CartDAO cartDAO;
    private ProductDAO productDAO;

    public CartService(CartDAO cartDAO, ProductDAO productDAO) {
        this.cartDAO = cartDAO;
        this.productDAO = productDAO;
    }

    public Cart addToCart(String customerId, String productId, int quantity) {
        Product product = productDAO.findById(productId);
        if (product == null || !product.isAvailable(quantity))
            throw new IllegalArgumentException("Product is not available: " + productId);
        Cart cart = cartDAO.findByCustomerId(customerId);
        cart.addItem(product, quantity);
        cartDAO.save(cart);
        return cart;
    }

    public Cart updateQuantity(String customerId, String productId, int quantity) {
        Cart cart = cartDAO.findByCustomerId(customerId);
        cart.updateQuantity(productId, quantity);
        cartDAO.save(cart);
        return cart;
    }

    public Cart removeItem(String customerId, String productId) {
        Cart cart = cartDAO.findByCustomerId(customerId);
        cart.removeItem(productId);
        cartDAO.save(cart);
        return cart;
    }

    public Cart viewCart(String customerId) {
        return cartDAO.findByCustomerId(customerId);
    }
}
