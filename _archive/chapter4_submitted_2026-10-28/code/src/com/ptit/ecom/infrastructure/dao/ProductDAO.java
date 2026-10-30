package com.ptit.ecom.infrastructure.dao;

import com.ptit.ecom.domain.product.Product;
import java.util.List;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public interface ProductDAO {
    Product findById(String productId);

    List<Product> searchByKeyword(String keyword, int limit);

    void decreaseStock(String productId, int quantity);
}
