package com.ptit.ecom.infrastructure.repository;

import com.ptit.ecom.domain.product.Product;
import java.util.List;

/**
 * Product repository, all_products() of slide A06.
 * Generated from the 4.4 design model (tools/model.py).
 */
public interface ProductRepository {
    List<Product> allProducts();

    Product findById(String productId);

    void decreaseStock(String productId, int quantity);

    void save(Product product);
}
