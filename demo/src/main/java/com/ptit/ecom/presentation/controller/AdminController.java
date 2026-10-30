package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.application.service.ProductService;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import java.math.BigDecimal;
import java.util.List;

/**
 * Administration controller: paintings and order states (UC12, UC13).
 * The WebServer only lets the administrator session reach these methods.
 */
public class AdminController {
    private ProductService productService;
    private OrderService orderService;

    public AdminController(ProductService productService, OrderService orderService) {
        this.productService = productService;
        this.orderService = orderService;
    }

    public List<Product> listProducts() {
        return productService.listProducts();
    }

    public Product updateProduct(String productId, BigDecimal price, int stockQuantity) {
        return productService.updatePriceAndStock(productId, price, stockQuantity);
    }

    public Painting addPainting(Painting painting) {
        return productService.addPainting(painting);
    }

    public List<Order> listAllOrders() {
        return orderService.listAllOrders();
    }

    public Order updateOrderStatus(String orderId, String status) {
        return orderService.updateStatus(orderId, OrderStatus.valueOf(status));
    }
}
