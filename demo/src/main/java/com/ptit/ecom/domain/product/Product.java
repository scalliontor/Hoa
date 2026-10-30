package com.ptit.ecom.domain.product;

import java.math.BigDecimal;

/**
 * Abstract catalogue product (slide A03: Product).
 * Generated from the 4.4 design model (tools/model.py).
 */
public abstract class Product {
    private String productId;
    private String name;
    private BigDecimal price;
    private int stockQuantity;
    private String imageUrl;
    private String description;

    public boolean isAvailable(int quantity) {
        return quantity > 0 && stockQuantity >= quantity;
    }

    public void decreaseStock(int quantity) {
        if (!isAvailable(quantity)) throw new IllegalStateException("Not enough stock for " + productId);
        stockQuantity -= quantity;
    }

    public abstract String getCategory();

    public String keywords() {
        StringBuilder text = new StringBuilder(name).append(' ').append(getCategory());
        if (description != null) text.append(' ').append(description);
        return text.toString().toLowerCase();
    }

    public String getProductId() {
        return productId;
    }

    public void setProductId(String productId) {
        this.productId = productId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public int getStockQuantity() {
        return stockQuantity;
    }

    public void setStockQuantity(int stockQuantity) {
        this.stockQuantity = stockQuantity;
    }

    public String getImageUrl() {
        return imageUrl;
    }

    public void setImageUrl(String imageUrl) {
        this.imageUrl = imageUrl;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}
