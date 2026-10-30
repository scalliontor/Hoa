package com.ptit.ecom.domain.product;

/**
 * Frame sold with a painting, a specialisation of Product (domain model 4.1).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Frame extends Product {
    private String material;
    private String color;
    private String sizeLabel;

    @Override
    public String getCategory() {
        return "FRAME";
    }

    @Override
    public String keywords() {
        return (super.keywords() + " " + material + " " + color).toLowerCase();
    }

    public String getMaterial() {
        return material;
    }

    public void setMaterial(String material) {
        this.material = material;
    }

    public String getColor() {
        return color;
    }

    public void setColor(String color) {
        this.color = color;
    }

    public String getSizeLabel() {
        return sizeLabel;
    }

    public void setSizeLabel(String sizeLabel) {
        this.sizeLabel = sizeLabel;
    }
}
