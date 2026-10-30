package com.ptit.ecom.domain.cart;

import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.product.Product;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class Cart {
    private String cartId;
    private LocalDateTime createdDate;
    private LocalDateTime updatedDate;
    private Customer owner;
    private List<CartItem> items = new ArrayList<>();

    public void addItem(Product product, int quantity) {
        if (quantity <= 0) throw new IllegalArgumentException("quantity must be greater than 0");
        for (CartItem item : items) {
            if (item.getProduct().getProductId().equals(product.getProductId())) {
                item.increase(quantity);
                updatedDate = LocalDateTime.now();
                return;
            }
        }
        items.add(new CartItem(product, quantity));
        updatedDate = LocalDateTime.now();
    }

    public void updateQuantity(String productId, int quantity) {
        if (quantity <= 0) {
            removeItem(productId);
            return;
        }
        for (CartItem item : items) {
            if (item.getProduct().getProductId().equals(productId)) item.setQuantity(quantity);
        }
        updatedDate = LocalDateTime.now();
    }

    public void removeItem(String productId) {
        items.removeIf(item -> item.getProduct().getProductId().equals(productId));
        updatedDate = LocalDateTime.now();
    }

    public BigDecimal calculateTotal() {
        BigDecimal total = BigDecimal.ZERO;
        for (CartItem item : items) total = total.add(item.getSubtotal());
        return total;
    }

    public boolean isEmpty() {
        return items.isEmpty();
    }

    public void clear() {
        items.clear();
        updatedDate = LocalDateTime.now();
    }

    public String getCartId() {
        return cartId;
    }

    public void setCartId(String cartId) {
        this.cartId = cartId;
    }

    public LocalDateTime getCreatedDate() {
        return createdDate;
    }

    public void setCreatedDate(LocalDateTime createdDate) {
        this.createdDate = createdDate;
    }

    public LocalDateTime getUpdatedDate() {
        return updatedDate;
    }

    public void setUpdatedDate(LocalDateTime updatedDate) {
        this.updatedDate = updatedDate;
    }

    public Customer getOwner() {
        return owner;
    }

    public void setOwner(Customer owner) {
        this.owner = owner;
    }

    public List<CartItem> getItems() {
        return items;
    }
}
