package com.ptit.ecom.domain.product;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class Electronics extends Product {
    private String brand;
    private int warrantyMonths;

    @Override
    public String getCategory() {
        return "ELECTRONICS";
    }

    public String getBrand() {
        return brand;
    }

    public void setBrand(String brand) {
        this.brand = brand;
    }

    public int getWarrantyMonths() {
        return warrantyMonths;
    }

    public void setWarrantyMonths(int warrantyMonths) {
        this.warrantyMonths = warrantyMonths;
    }
}
