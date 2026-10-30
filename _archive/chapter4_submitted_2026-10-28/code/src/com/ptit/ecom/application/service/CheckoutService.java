package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.cart.CartItem;
import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderItem;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.order.Shipping;
import com.ptit.ecom.domain.order.ShippingStatus;
import com.ptit.ecom.domain.payment.Payment;
import com.ptit.ecom.domain.payment.PaymentStatus;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.dao.CartDAO;
import com.ptit.ecom.infrastructure.dao.CustomerDAO;
import com.ptit.ecom.infrastructure.dao.OrderDAO;
import com.ptit.ecom.infrastructure.dao.ProductDAO;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class CheckoutService {
    private CartDAO cartDAO;
    private OrderDAO orderDAO;
    private ProductDAO productDAO;
    private CustomerDAO customerDAO;

    public CheckoutService(CartDAO cartDAO, OrderDAO orderDAO, ProductDAO productDAO, CustomerDAO customerDAO) {
        this.cartDAO = cartDAO;
        this.orderDAO = orderDAO;
        this.productDAO = productDAO;
        this.customerDAO = customerDAO;
    }

    public Order checkout(String customerId, String addressId, Payment payment) {
        Cart cart = cartDAO.findByCustomerId(customerId);
        if (cart == null || cart.isEmpty()) throw new IllegalStateException("Cart is empty");
        Customer customer = customerDAO.findById(customerId);

        Order order = new Order();
        order.setCustomer(customer);
        order.setOrderDate(LocalDateTime.now());
        order.setStatus(OrderStatus.PLACED);
        for (CartItem item : cart.getItems()) {
            // Price and stock are read again from the catalogue, not trusted from the cart.
            Product current = productDAO.findById(item.getProduct().getProductId());
            if (!current.isAvailable(item.getQuantity()))
                throw new IllegalStateException("Out of stock: " + current.getName());
            order.addItem(OrderItem.fromCartItem(item, current));
        }

        Shipping shipping = new Shipping();
        shipping.setAddress(customer.findAddress(addressId));
        shipping.setShippingFee(BigDecimal.ZERO);
        shipping.setStatus(ShippingStatus.PREPARING);
        order.setShipping(shipping);
        order.calculateTotal(customer.getDiscountRate());

        payment.setAmount(order.getTotalAmount());
        payment.setStatus(PaymentStatus.PENDING);
        order.addPayment(payment);

        // save, decreaseStock and clear must run in one database transaction.
        orderDAO.save(order);
        for (OrderItem item : order.getItems())
            productDAO.decreaseStock(item.getProduct().getProductId(), item.getQuantity());
        cartDAO.clear(cart.getCartId());
        return order;
    }
}
