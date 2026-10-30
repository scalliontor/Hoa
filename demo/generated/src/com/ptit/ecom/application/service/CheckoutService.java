package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.payment.Payment;
import com.ptit.ecom.infrastructure.repository.CartRepository;
import com.ptit.ecom.infrastructure.repository.CustomerRepository;
import com.ptit.ecom.infrastructure.repository.OrderRepository;
import com.ptit.ecom.infrastructure.repository.ProductRepository;

/**
 * CheckoutService.checkout(cartID) of slide A05: coordinates the checkout.
 * Generated from the 4.4 design model (tools/model.py).
 */
public class CheckoutService {
    private CartRepository cartRepository;
    private OrderRepository orderRepository;
    private ProductRepository productRepository;
    private CustomerRepository customerRepository;

    public CheckoutService(CartRepository cartRepository, OrderRepository orderRepository, ProductRepository productRepository, CustomerRepository customerRepository) {
        throw new UnsupportedOperationException("TODO: CheckoutService");
    }

    public Order checkout(String cartId, String customerId, String addressId, Payment payment) {
        throw new UnsupportedOperationException("TODO: checkout");
    }
}
