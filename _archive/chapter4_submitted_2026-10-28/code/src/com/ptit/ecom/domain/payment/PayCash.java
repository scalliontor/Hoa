package com.ptit.ecom.domain.payment;

import java.math.BigDecimal;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
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

    public BigDecimal getCashReceived() {
        return cashReceived;
    }

    public void setCashReceived(BigDecimal cashReceived) {
        this.cashReceived = cashReceived;
    }

    public BigDecimal getChangeAmount() {
        return changeAmount;
    }

    public void setChangeAmount(BigDecimal changeAmount) {
        this.changeAmount = changeAmount;
    }
}
