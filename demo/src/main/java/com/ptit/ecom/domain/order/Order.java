package com.ptit.ecom.domain.order;

import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.payment.Payment;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Order: the confirmed transaction produced by checkout (slides A03/A05).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Order {
    private String orderId;
    private LocalDateTime orderDate;
    private OrderStatus status;
    private BigDecimal totalAmount;
    private Customer customer;
    private List<OrderItem> items = new ArrayList<>();
    private Shipping shipping;
    private List<Payment> payments = new ArrayList<>();

    public void addItem(OrderItem item) {
        items.add(item);
    }

    public void addPayment(Payment payment) {
        payments.add(payment);
    }

    public BigDecimal calculateTotal(BigDecimal discountRate) {
        BigDecimal subtotal = BigDecimal.ZERO;
        for (OrderItem item : items) subtotal = subtotal.add(item.getSubtotal());
        BigDecimal discount = subtotal.multiply(discountRate);
        BigDecimal fee = shipping == null ? BigDecimal.ZERO : shipping.getShippingFee();
        totalAmount = subtotal.subtract(discount).add(fee).max(BigDecimal.ZERO);
        return totalAmount;
    }

    public void cancel() {
        if (status != OrderStatus.PLACED && status != OrderStatus.PROCESSING)
            throw new IllegalStateException("Only placed or processing orders can be cancelled");
        status = OrderStatus.CANCELLED;
    }

    public void advanceTo(OrderStatus next) {
        boolean allowed = (status == OrderStatus.PLACED && next == OrderStatus.PROCESSING)
                || (status == OrderStatus.PROCESSING && next == OrderStatus.SHIPPED)
                || (status == OrderStatus.SHIPPED && next == OrderStatus.DELIVERED);
        if (!allowed) throw new IllegalStateException("Cannot move order " + orderId + " from " + status + " to " + next);
        status = next;
    }

    public boolean isOwnedBy(String customerId) {
        return customer != null && customer.getCustomerId().equals(customerId);
    }

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
    }

    public LocalDateTime getOrderDate() {
        return orderDate;
    }

    public void setOrderDate(LocalDateTime orderDate) {
        this.orderDate = orderDate;
    }

    public OrderStatus getStatus() {
        return status;
    }

    public void setStatus(OrderStatus status) {
        this.status = status;
    }

    public BigDecimal getTotalAmount() {
        return totalAmount;
    }

    public void setTotalAmount(BigDecimal totalAmount) {
        this.totalAmount = totalAmount;
    }

    public Customer getCustomer() {
        return customer;
    }

    public void setCustomer(Customer customer) {
        this.customer = customer;
    }

    public List<OrderItem> getItems() {
        return items;
    }

    public Shipping getShipping() {
        return shipping;
    }

    public void setShipping(Shipping shipping) {
        this.shipping = shipping;
    }

    public List<Payment> getPayments() {
        return payments;
    }
}
