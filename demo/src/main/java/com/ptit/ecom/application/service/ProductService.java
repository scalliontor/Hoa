package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.ProductRepository;
import java.math.BigDecimal;
import java.util.List;
import java.util.NoSuchElementException;

/**
 * Product management for the administrator (use case UC12).
 * Price and stock can never be negative; a new painting gets the next free id P01, P02, ...
 */
public class ProductService {
    private ProductRepository productRepository;

    public ProductService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public List<Product> listProducts() {
        return productRepository.allProducts();
    }

    public Product updatePriceAndStock(String productId, BigDecimal price, int stockQuantity) {
        Product product = productRepository.findById(productId);
        if (product == null) throw new NoSuchElementException("Product " + productId + " does not exist");
        if (price == null || price.signum() < 0 || stockQuantity < 0) {
            throw new IllegalArgumentException("Price and stock must not be negative");
        }
        product.setPrice(price);
        product.setStockQuantity(stockQuantity);
        productRepository.save(product);
        return product;
    }

    public Painting addPainting(Painting painting) {
        if (painting.getName() == null || painting.getName().isBlank() || painting.getArtist() == null) {
            throw new IllegalArgumentException("A painting needs a title and an artist");
        }
        if (painting.getPrice() == null || painting.getPrice().signum() < 0 || painting.getStockQuantity() < 0) {
            throw new IllegalArgumentException("Price and stock must not be negative");
        }
        painting.setProductId(nextPaintingId());
        productRepository.save(painting);
        return painting;
    }

    private String nextPaintingId() {
        int highest = 0;
        for (Product product : productRepository.allProducts()) {
            String id = product.getProductId();
            if (id.matches("P\\d+")) highest = Math.max(highest, Integer.parseInt(id.substring(1)));
        }
        return String.format("P%02d", highest + 1);
    }
}
