package com.ptit.ecom.domain.customer;

import java.time.LocalDate;

/**
 * New customer with a welcome voucher (Kiem tra 01).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class CustomerNew extends Customer {
    private LocalDate registeredDate;
    private String welcomeVoucher;

    public boolean hasWelcomeVoucher() {
        return welcomeVoucher != null && !welcomeVoucher.trim().isEmpty();
    }

    public LocalDate getRegisteredDate() {
        return registeredDate;
    }

    public void setRegisteredDate(LocalDate registeredDate) {
        this.registeredDate = registeredDate;
    }

    public String getWelcomeVoucher() {
        return welcomeVoucher;
    }

    public void setWelcomeVoucher(String welcomeVoucher) {
        this.welcomeVoucher = welcomeVoucher;
    }
}
