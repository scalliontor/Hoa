package com.ptit.ecom.domain.cart;

import com.ptit.ecom.domain.product.Product;
import java.math.BigDecimal;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class CartItem {
    private int quantity;
    private BigDecimal cartPrice;
    private Product product;

    public CartItem() {
    }

    public CartItem(Product product, int quantity) {
        this.product = product;
        this.quantity = quantity;
        this.cartPrice = product.getPrice();
    }

    public BigDecimal getSubtotal() {
        return cartPrice.multiply(BigDecimal.valueOf(quantity));
    }

    public void increase(int quantity) {
        this.quantity += quantity;
    }

    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }

    public BigDecimal getCartPrice() {
        return cartPrice;
    }

    public void setCartPrice(BigDecimal cartPrice) {
        this.cartPrice = cartPrice;
    }

    public Product getProduct() {
        return product;
    }

    public void setProduct(Product product) {
        this.product = product;
    }
}
