package com.ptit.ecom.application.search;

import com.ptit.ecom.domain.product.Product;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class SearchResult {
    private Product product;
    private double score;

    public SearchResult(Product product, double score) {
        this.product = product;
        this.score = score;
    }

    public Product getProduct() {
        return product;
    }

    public void setProduct(Product product) {
        this.product = product;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
    }
}
