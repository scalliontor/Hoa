package com.ptit.ecom.application.service;

import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.cart.CartItem;
import com.ptit.ecom.domain.customer.Address;
import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderItem;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.order.Shipping;
import com.ptit.ecom.domain.order.ShippingStatus;
import com.ptit.ecom.domain.payment.PayCredit;
import com.ptit.ecom.domain.payment.Payment;
import com.ptit.ecom.domain.payment.PaymentStatus;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.CartRepository;
import com.ptit.ecom.infrastructure.repository.CustomerRepository;
import com.ptit.ecom.infrastructure.repository.OrderRepository;
import com.ptit.ecom.infrastructure.repository.ProductRepository;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.ThreadLocalRandom;

/**
 * CheckoutService.checkout(cartID) of slide A05: coordinates the checkout.
 * Cart -> checkout -> Order (slide A03): CartItems become OrderItems at the current catalogue price.
 */
public class CheckoutService {
    private static final BigDecimal SHIPPING_FEE = new BigDecimal("8");
    private CartRepository cartRepository;
    private OrderRepository orderRepository;
    private ProductRepository productRepository;
    private CustomerRepository customerRepository;

    public CheckoutService(CartRepository cartRepository, OrderRepository orderRepository,
                           ProductRepository productRepository, CustomerRepository customerRepository) {
        this.cartRepository = cartRepository;
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
        this.customerRepository = customerRepository;
    }

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

    /**
     * Saves a delivery address typed at checkout (UC07). Every part is required and must fit its database column
     * (house number 20, street 100, district 60, city 60 characters), so a bad entry is refused before anything is stored.
     */
    public Address addAddress(String customerId, Address address) {
        if (customerRepository.findById(customerId) == null) {
            throw new IllegalArgumentException("Unknown customer " + customerId);
        }
        address.setHouseNumber(required("House number", address.getHouseNumber(), 20));
        address.setStreet(required("Street", address.getStreet(), 100));
        address.setDistrict(required("District", address.getDistrict(), 60));
        address.setCity(required("City", address.getCity(), 60));
        return customerRepository.saveAddress(customerId, address);
    }

    private static String required(String label, String value, int maxLength) {
        String trimmed = value == null ? "" : value.trim().replaceAll("\\s+", " ");
        if (trimmed.isEmpty()) throw new IllegalArgumentException(label + " is required");
        if (trimmed.length() > maxLength) {
            throw new IllegalArgumentException(label + " must be at most " + maxLength + " characters");
        }
        return trimmed;
    }

    private Order newOrder(Customer customer) {
        Order order = new Order();
        String stamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyMMddHHmmss"));
        order.setOrderId(stamp + ThreadLocalRandom.current().nextInt(10, 100));
        order.setCustomer(customer);
        order.setOrderDate(LocalDateTime.now().withNano(0));
        order.setStatus(OrderStatus.PLACED);
        return order;
    }

    /** Price and stock are read again from the catalogue, not trusted from the cart. */
    private Product currentProduct(CartItem item) {
        Product current = productRepository.findById(item.getProduct().getProductId());
        if (current == null || !current.isAvailable(item.getQuantity())) {
            throw new IllegalStateException("Out of stock: " + item.getProduct().getName());
        }
        return current;
    }

    private Shipping newShipping(Order order, Address address) {
        Shipping shipping = new Shipping();
        shipping.setShippingId("SH-" + order.getOrderId());
        shipping.setCarrier("GHN Express");
        shipping.setShippingFee(SHIPPING_FEE);
        shipping.setStatus(ShippingStatus.PREPARING);
        shipping.setAddress(address);
        return shipping;
    }

    /** Cash is collected on delivery (PENDING); a card must be authorised now (polymorphic process()). */
    private Payment pay(Order order, Payment payment) {
        payment.setPaymentId("PAY-" + order.getOrderId());
        payment.setAmount(order.getTotalAmount());
        payment.setStatus(PaymentStatus.PENDING);
        if (payment instanceof PayCredit && !payment.process()) {
            throw new IllegalStateException("The card payment was declined");
        }
        return payment;
    }
}
