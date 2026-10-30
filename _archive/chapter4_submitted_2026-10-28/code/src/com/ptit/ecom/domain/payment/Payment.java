package com.ptit.ecom.domain.payment;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public abstract class Payment {
    private String paymentId;
    private BigDecimal amount;
    private LocalDateTime paymentDate;
    private PaymentStatus status;

    public abstract boolean process();

    public void markSucceeded() {
        status = PaymentStatus.SUCCEEDED;
        paymentDate = LocalDateTime.now();
    }

    public void markFailed() {
        status = PaymentStatus.FAILED;
    }

    public String getPaymentId() {
        return paymentId;
    }

    public void setPaymentId(String paymentId) {
        this.paymentId = paymentId;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public LocalDateTime getPaymentDate() {
        return paymentDate;
    }

    public void setPaymentDate(LocalDateTime paymentDate) {
        this.paymentDate = paymentDate;
    }

    public PaymentStatus getStatus() {
        return status;
    }

    public void setStatus(PaymentStatus status) {
        this.status = status;
    }
}
