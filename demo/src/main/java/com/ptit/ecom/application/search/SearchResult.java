package com.ptit.ecom.application.search;

import com.ptit.ecom.domain.product.Product;

/**
 * One search result with its partial scores (slide A06).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class SearchResult {
    private Product product;
    private double textScore;
    private double imageScore;
    private double businessScore;
    private double score;
    private String reason;

    public SearchResult(Product product) {
        this.product = product;
    }

    public Product getProduct() {
        return product;
    }

    public void setProduct(Product product) {
        this.product = product;
    }

    public double getTextScore() {
        return textScore;
    }

    public void setTextScore(double textScore) {
        this.textScore = textScore;
    }

    public double getImageScore() {
        return imageScore;
    }

    public void setImageScore(double imageScore) {
        this.imageScore = imageScore;
    }

    public double getBusinessScore() {
        return businessScore;
    }

    public void setBusinessScore(double businessScore) {
        this.businessScore = businessScore;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
    }

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }
}
