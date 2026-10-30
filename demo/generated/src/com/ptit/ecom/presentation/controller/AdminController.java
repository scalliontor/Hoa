package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.application.service.ProductService;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import java.math.BigDecimal;
import java.util.List;

/**
 * Administration controller: paintings and order states (UC12, UC13).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class AdminController {
    private ProductService productService;
    private OrderService orderService;

    public AdminController(ProductService productService, OrderService orderService) {
        throw new UnsupportedOperationException("TODO: AdminController");
    }

    public List<Product> listProducts() {
        throw new UnsupportedOperationException("TODO: listProducts");
    }

    public Product updateProduct(String productId, BigDecimal price, int stockQuantity) {
        throw new UnsupportedOperationException("TODO: updateProduct");
    }

    public Painting addPainting(Painting painting) {
        throw new UnsupportedOperationException("TODO: addPainting");
    }

    public List<Order> listAllOrders() {
        throw new UnsupportedOperationException("TODO: listAllOrders");
    }

    public Order updateOrderStatus(String orderId, String status) {
        throw new UnsupportedOperationException("TODO: updateOrderStatus");
    }
}
