package com.ptit.ecom.domain.product;

/**
 * Product category: classifies every product and names its detail kind (domain model 4.1).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Category {
    private String categoryId;
    private String name;
    private DetailKind detailKind;
    private String description;

    public boolean accepts(Product product) {
        return product.getDetailKind() == detailKind;
    }

    public String getCategoryId() {
        return categoryId;
    }

    public void setCategoryId(String categoryId) {
        this.categoryId = categoryId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public DetailKind getDetailKind() {
        return detailKind;
    }

    public void setDetailKind(DetailKind detailKind) {
        this.detailKind = detailKind;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}
