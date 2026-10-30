package com.ptit.ecom.domain.product;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class Clothes extends Product {
    private String brand;
    private String size;
    private String color;
    private String material;

    @Override
    public String getCategory() {
        return "CLOTHES";
    }

    public String getBrand() {
        return brand;
    }

    public void setBrand(String brand) {
        this.brand = brand;
    }

    public String getSize() {
        return size;
    }

    public void setSize(String size) {
        this.size = size;
    }

    public String getColor() {
        return color;
    }

    public void setColor(String color) {
        this.color = color;
    }

    public String getMaterial() {
        return material;
    }

    public void setMaterial(String material) {
        this.material = material;
    }
}
