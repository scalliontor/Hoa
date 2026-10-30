package com.ptit.ecom.domain.product;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class Shoes extends Product {
    private String brand;
    private int size;
    private String color;

    @Override
    public String getCategory() {
        return "SHOES";
    }

    public String getBrand() {
        return brand;
    }

    public void setBrand(String brand) {
        this.brand = brand;
    }

    public int getSize() {
        return size;
    }

    public void setSize(int size) {
        this.size = size;
    }

    public String getColor() {
        return color;
    }

    public void setColor(String color) {
        this.color = color;
    }
}
