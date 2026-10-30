package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.ProductRepository;
import java.math.BigDecimal;
import java.util.List;

/**
 * Product management for the administrator (use case UC12).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class ProductService {
    private ProductRepository productRepository;

    public ProductService(ProductRepository productRepository) {
        throw new UnsupportedOperationException("TODO: ProductService");
    }

    public List<Product> listProducts() {
        throw new UnsupportedOperationException("TODO: listProducts");
    }

    public Product updatePriceAndStock(String productId, BigDecimal price, int stockQuantity) {
        throw new UnsupportedOperationException("TODO: updatePriceAndStock");
    }

    public Painting addPainting(Painting painting) {
        throw new UnsupportedOperationException("TODO: addPainting");
    }
}
