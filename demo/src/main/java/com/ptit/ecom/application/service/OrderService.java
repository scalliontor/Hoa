package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.infrastructure.repository.OrderRepository;
import java.util.List;
import java.util.NoSuchElementException;

/**
 * Order service: lookups check ownership (slide A05, NFR01).
 * "Not found" and "not yours" give the same answer, so order numbers of others leak nothing.
 */
public class OrderService {
    private OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    /** find my order 20261001 (slide A06): only an order of the signed-in customer is returned. */
    public Order getOrder(String customerId, String orderId) {
        Order order = orderRepository.findOrder(orderId);
        if (order == null || !order.isOwnedBy(customerId)) {
            throw new NoSuchElementException("Order " + orderId + " was not found in your account");
        }
        return order;
    }

    public List<Order> listOrders(String customerId) {
        return orderRepository.findByCustomer(customerId);
    }

    /** where is my latest order? (slide A06): the newest order, or null if there is none. */
    public Order latestOrder(String customerId) {
        List<Order> orders = listOrders(customerId);
        return orders.isEmpty() ? null : orders.get(0);
    }

    /** UC11: Order.cancel() allows it only before shipment (PLACED or PROCESSING). */
    public void cancelOrder(String customerId, String orderId) {
        Order order = getOrder(customerId, orderId);
        order.cancel();
        orderRepository.updateStatus(orderId, order.getStatus());
    }

    public List<Order> listAllOrders() {
        return orderRepository.allOrders();
    }

    /** UC13: Order.advanceTo() allows only PLACED -> PROCESSING -> SHIPPED -> DELIVERED. */
    public Order updateStatus(String orderId, OrderStatus status) {
        Order order = orderRepository.findOrder(orderId);
        if (order == null) throw new NoSuchElementException("Order " + orderId + " does not exist");
        order.advanceTo(status);
        orderRepository.updateStatus(orderId, status);
        return orderRepository.findOrder(orderId);
    }
}
