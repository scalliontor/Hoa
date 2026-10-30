package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.CheckoutService;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.payment.PayCash;
import com.ptit.ecom.domain.payment.PayCredit;
import com.ptit.ecom.domain.payment.Payment;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class CheckoutController {
    private CheckoutService checkoutService;

    public CheckoutController(CheckoutService checkoutService) {
        this.checkoutService = checkoutService;
    }

    public Order checkout(String customerId, String addressId, String paymentMethod) {
        Payment payment = "CASH".equalsIgnoreCase(paymentMethod) ? new PayCash() : new PayCredit();
        return checkoutService.checkout(customerId, addressId, payment);
    }
}
