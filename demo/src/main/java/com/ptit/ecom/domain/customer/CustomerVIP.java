package com.ptit.ecom.domain.customer;

import java.math.BigDecimal;

/**
 * VIP customer with a discount: polymorphic getDiscountRate (Kiem tra 01).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class CustomerVIP extends Customer {
    private int vipLevel;
    private BigDecimal discountRate;
    private int rewardPoints;

    @Override
    public BigDecimal getDiscountRate() {
        return discountRate;
    }

    public void addPoints(int points) {
        if (points < 0) throw new IllegalArgumentException("points must not be negative");
        rewardPoints += points;
    }

    public int getVipLevel() {
        return vipLevel;
    }

    public void setVipLevel(int vipLevel) {
        this.vipLevel = vipLevel;
    }

    public void setDiscountRate(BigDecimal discountRate) {
        this.discountRate = discountRate;
    }

    public int getRewardPoints() {
        return rewardPoints;
    }

    public void setRewardPoints(int rewardPoints) {
        this.rewardPoints = rewardPoints;
    }
}
