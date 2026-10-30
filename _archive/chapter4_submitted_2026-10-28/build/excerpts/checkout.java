public class CheckoutService {
    private CartDAO cartDAO;
    private OrderDAO orderDAO;
    private ProductDAO productDAO;
    private CustomerDAO customerDAO;
    // ... constructor injecting the four DAOs omitted

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
