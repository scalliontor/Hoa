package com.ptit.ecom.domain.order;

import com.ptit.ecom.domain.cart.CartItem;
import com.ptit.ecom.domain.product.Product;
import java.math.BigDecimal;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class OrderItem {
    private int quantity;
    private BigDecimal unitPrice;
    private Product product;

    public static OrderItem fromCartItem(CartItem item, Product current) {
        OrderItem orderItem = new OrderItem();
        orderItem.product = current;
        orderItem.quantity = item.getQuantity();
        orderItem.unitPrice = current.getPrice();
        return orderItem;
    }

    public BigDecimal getSubtotal() {
        return unitPrice.multiply(BigDecimal.valueOf(quantity));
    }

    public int getQuantity() {
        return quantity;
    }

    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public void setUnitPrice(BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
    }

    public Product getProduct() {
        return product;
    }

    public void setProduct(Product product) {
        this.product = product;
    }
}
