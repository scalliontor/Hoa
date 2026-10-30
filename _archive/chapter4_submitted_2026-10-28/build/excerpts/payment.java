public abstract class Payment {
    private String paymentId;
    private BigDecimal amount;
    private LocalDateTime paymentDate;
    private PaymentStatus status;

    public abstract boolean process();
    // ... other members and generated accessors omitted
}

public class PayCash extends Payment {
    private BigDecimal cashReceived;
    private BigDecimal changeAmount;

    @Override
    public boolean process() {
        if (cashReceived == null || cashReceived.compareTo(getAmount()) < 0) {
            markFailed();
            return false;
        }
        changeAmount = cashReceived.subtract(getAmount());
        markSucceeded();
        return true;
    }
    // ... other members and generated accessors omitted
}
