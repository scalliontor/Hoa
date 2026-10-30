public class OrderService {
    // ...
    /** find my order 20261001 (slide A06): only an order of the signed-in customer is returned. */
    public Order getOrder(String customerId, String orderId) {
        Order order = orderRepository.findOrder(orderId);
        if (order == null || !order.isOwnedBy(customerId)) {
            throw new NoSuchElementException("Order " + orderId + " was not found in your account");
        }
        return order;
    }
    // ...
    /** UC11: Order.cancel() allows it only before shipment (PLACED or PROCESSING). */
    public void cancelOrder(String customerId, String orderId) {
        Order order = getOrder(customerId, orderId);
        order.cancel();
        orderRepository.updateStatus(orderId, order.getStatus());
    }
    // ...
    /** UC13: Order.advanceTo() allows only PLACED -> PROCESSING -> SHIPPED -> DELIVERED. */
    public Order updateStatus(String orderId, OrderStatus status) {
        Order order = orderRepository.findOrder(orderId);
        if (order == null) throw new NoSuchElementException("Order " + orderId + " does not exist");
        order.advanceTo(status);
        orderRepository.updateStatus(orderId, status);
        return orderRepository.findOrder(orderId);
    }
    // ...
}
