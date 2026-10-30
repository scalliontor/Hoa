package com.ptit.ecom.application.search;

import java.math.BigDecimal;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class CommonQuery {
    private String mode;
    private String text;
    private float[] imageVector;
    private BigDecimal maxPrice;

    public CommonQuery(String mode, String text, float[] imageVector, BigDecimal maxPrice) {
        this.mode = mode;
        this.text = text;
        this.imageVector = imageVector;
        this.maxPrice = maxPrice;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public float[] getImageVector() {
        return imageVector;
    }

    public void setImageVector(float[] imageVector) {
        this.imageVector = imageVector;
    }

    public BigDecimal getMaxPrice() {
        return maxPrice;
    }

    public void setMaxPrice(BigDecimal maxPrice) {
        this.maxPrice = maxPrice;
    }
}
