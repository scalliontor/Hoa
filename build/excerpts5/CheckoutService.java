public class CheckoutService {
    // ...
    /** The steps of slide A05: get the cart, check it, create the order and its items, pay, save, clear. */
    public Order checkout(String cartId, String customerId, String addressId, Payment payment) {
        Cart cart = cartRepository.findById(cartId);
        if (cart == null || !cart.getOwner().getCustomerId().equals(customerId)) {
            throw new IllegalArgumentException("This cart does not belong to your account");
        }
        if (cart.isEmpty()) throw new IllegalStateException("Your cart is empty");
        Customer customer = customerRepository.findById(customerId);
        Order order = newOrder(customer);
        for (CartItem item : cart.getItems()) order.addItem(OrderItem.fromCartItem(item, currentProduct(item)));
        order.setShipping(newShipping(order, customer.findAddress(addressId)));
        order.calculateTotal(customer.getDiscountRate());
        order.addPayment(pay(order, payment));
        orderRepository.save(order);
        for (OrderItem item : order.getItems()) {
            productRepository.decreaseStock(item.getProduct().getProductId(), item.getQuantity());
        }
        cartRepository.clear(cartId);
        return order;
    }
    // ...
    /** Price and stock are read again from the catalogue, not trusted from the cart. */
    private Product currentProduct(CartItem item) {
        Product current = productRepository.findById(item.getProduct().getProductId());
        if (current == null || !current.isAvailable(item.getQuantity())) {
            throw new IllegalStateException("Out of stock: " + item.getProduct().getName());
        }
        return current;
    }
    // ...
}
