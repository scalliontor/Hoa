import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.cart.CartItem;
import com.ptit.ecom.domain.customer.CustomerVIP;
import com.ptit.ecom.domain.customer.FullName;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.order.OrderItem;
import com.ptit.ecom.domain.order.OrderStatus;
import com.ptit.ecom.domain.order.Shipping;
import com.ptit.ecom.domain.payment.PayCash;
import com.ptit.ecom.domain.payment.PaymentStatus;
import com.ptit.ecom.domain.product.Book;
import com.ptit.ecom.domain.product.Laptop;
import java.math.BigDecimal;

/** Hand-written checks of the domain behaviour in the generated code (not generated). */
public class DomainSmokeTest {
    private static int passed;

    public static void main(String[] args) {
        Book book = new Book();
        book.setProductId("P001");
        book.setName("Clean Code");
        book.setPrice(new BigDecimal("150000"));
        book.setStockQuantity(10);

        Laptop laptop = new Laptop();
        laptop.setProductId("P002");
        laptop.setName("ThinkPad X1");
        laptop.setPrice(new BigDecimal("30000000"));
        laptop.setStockQuantity(2);

        // 1. Adding the same product twice merges the cart line.
        Cart cart = new Cart();
        cart.addItem(book, 1);
        cart.addItem(book, 2);
        check("Cart.addItem merges the same product into one line",
                cart.getItems().size() == 1 && cart.getItems().get(0).getQuantity() == 3);
        cart.addItem(laptop, 1);
        check("Cart.calculateTotal = 3 x 150000 + 1 x 30000000 = 30450000",
                same(cart.calculateTotal(), "30450000"));

        // 2. OrderItem keeps the price read at checkout, not later catalogue changes.
        CartItem bookLine = cart.getItems().get(0);
        book.setPrice(new BigDecimal("160000"));
        OrderItem bookItem = OrderItem.fromCartItem(bookLine, book);
        book.setPrice(new BigDecimal("170000"));
        check("OrderItem.fromCartItem snapshots the current price 160000 (cart price was 150000)",
                same(bookItem.getUnitPrice(), "160000") && same(bookLine.getCartPrice(), "150000")
                        && bookItem.getQuantity() == 3);

        // 3. Order total = subtotal - VIP discount + shipping fee.
        Order order = new Order();
        order.setStatus(OrderStatus.PLACED);
        order.addItem(bookItem);
        order.addItem(OrderItem.fromCartItem(cart.getItems().get(1), laptop));
        Shipping shipping = new Shipping();
        shipping.setShippingFee(new BigDecimal("30000"));
        order.setShipping(shipping);
        CustomerVIP vip = new CustomerVIP();
        vip.setDiscountRate(new BigDecimal("0.10"));
        BigDecimal total = order.calculateTotal(vip.getDiscountRate());
        check("Order.calculateTotal: 30480000 - 10% + 30000 = 27462000 (got " + total.toPlainString() + ")",
                same(total, "27462000") && same(order.getTotalAmount(), "27462000"));

        // 4. Cancellation is allowed only before shipping.
        order.cancel();
        check("Order.cancel moves a PLACED order to CANCELLED", order.getStatus() == OrderStatus.CANCELLED);
        Order shipped = new Order();
        shipped.setStatus(OrderStatus.SHIPPED);
        check("Order.cancel rejects a SHIPPED order", throwsIllegalState(shipped::cancel)
                && shipped.getStatus() == OrderStatus.SHIPPED);

        // 5. Cash payment succeeds only when enough cash is received.
        PayCash enough = new PayCash();
        enough.setAmount(new BigDecimal("500000"));
        enough.setCashReceived(new BigDecimal("600000"));
        check("PayCash.process with 600000 for 500000 succeeds, change 100000",
                enough.process() && same(enough.getChangeAmount(), "100000")
                        && enough.getStatus() == PaymentStatus.SUCCEEDED);
        PayCash short_ = new PayCash();
        short_.setAmount(new BigDecimal("500000"));
        short_.setCashReceived(new BigDecimal("400000"));
        check("PayCash.process with 400000 for 500000 fails",
                !short_.process() && short_.getStatus() == PaymentStatus.FAILED);

        // 6. Stock can not go below zero.
        laptop.decreaseStock(2);
        check("Product.decreaseStock(2) leaves 0 laptops", laptop.getStockQuantity() == 0);
        check("Product.decreaseStock(1) on empty stock is rejected", throwsIllegalState(() -> laptop.decreaseStock(1)));

        // 7. Vietnamese name order.
        FullName name = new FullName();
        name.setFirstName("Anh");
        name.setMiddleName("Hùng");
        name.setLastName("Vũ");
        check("FullName.getDisplayName = \"Vũ Hùng Anh\"", "Vũ Hùng Anh".equals(name.getDisplayName()));

        System.out.println("ALL CHECKS PASSED (" + passed + "/" + passed + ")");
    }

    private static boolean same(BigDecimal value, String expected) {
        return value != null && value.compareTo(new BigDecimal(expected)) == 0;
    }

    private static boolean throwsIllegalState(Runnable action) {
        try {
            action.run();
            return false;
        } catch (IllegalStateException expected) {
            return true;
        }
    }

    private static void check(String label, boolean ok) {
        if (!ok) {
            System.out.println("FAIL " + label);
            System.exit(1);
        }
        passed++;
        System.out.println("PASS " + label);
    }
}
