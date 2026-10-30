public class OrderItem {
    private int quantity;
    private BigDecimal unitPrice;
    private Product product;

    public static OrderItem fromCartItem(CartItem item, Product current) {
        OrderItem orderItem = new OrderItem();
        orderItem.product = current;
        orderItem.quantity = item.getQuantity();
        orderItem.unitPrice = current.getPrice();
        return orderItem;
    }

    public BigDecimal getSubtotal() {
        return unitPrice.multiply(BigDecimal.valueOf(quantity));
    }
    // ... other members and generated accessors omitted
}
