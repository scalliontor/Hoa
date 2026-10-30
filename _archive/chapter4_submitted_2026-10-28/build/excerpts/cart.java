public class Cart {
    private String cartId;
    private LocalDateTime createdDate;
    private LocalDateTime updatedDate;
    private Customer owner;

    public void addItem(Product product, int quantity) {
        if (quantity <= 0) throw new IllegalArgumentException("quantity must be greater than 0");
        for (CartItem item : items) {
            if (item.getProduct().getProductId().equals(product.getProductId())) {
                item.increase(quantity);
                updatedDate = LocalDateTime.now();
                return;
            }
        }
        items.add(new CartItem(product, quantity));
        updatedDate = LocalDateTime.now();
    }

    public BigDecimal calculateTotal() {
        BigDecimal total = BigDecimal.ZERO;
        for (CartItem item : items) total = total.add(item.getSubtotal());
        return total;
    }
    // ... other members and generated accessors omitted
}
