package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.CheckoutService;
import com.ptit.ecom.domain.customer.Address;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.payment.PayCash;
import com.ptit.ecom.domain.payment.PayCredit;
import com.ptit.ecom.domain.payment.Payment;
import java.util.UUID;

/**
 * CheckoutController of slide A05.
 * paymentMethod is "CASH" or "CARD:<last 4 digits>:<card holder>"; the full card number never reaches the server.
 */
public class CheckoutController {
    private CheckoutService checkoutService;

    public CheckoutController(CheckoutService checkoutService) {
        this.checkoutService = checkoutService;
    }

    public Order checkout(String customerId, String cartId, String addressId, String paymentMethod) {
        return checkoutService.checkout(cartId, customerId, addressId, toPayment(paymentMethod));
    }

    /** A delivery address typed by the customer at checkout; the customer id comes from the session. */
    public Address addAddress(String customerId, String houseNumber, String street, String district, String city) {
        Address address = new Address();
        address.setHouseNumber(houseNumber);
        address.setStreet(street);
        address.setDistrict(district);
        address.setCity(city);
        return checkoutService.addAddress(customerId, address);
    }

    /** Builds the Payment subclass; the card authorisation of a real provider is simulated here. */
    private static Payment toPayment(String paymentMethod) {
        if (paymentMethod == null || !paymentMethod.startsWith("CARD")) return new PayCash();
        String[] parts = paymentMethod.split(":", 3);
        if (parts.length < 2 || !parts[1].matches("\\d{4}")) {
            throw new IllegalArgumentException("Please enter the last four digits of the card");
        }
        PayCredit credit = new PayCredit();
        credit.setCardLast4(parts[1]);
        credit.setCardHolder(parts.length > 2 ? parts[2] : "");
        credit.setBankName("Demo card");
        credit.setAuthorizationCode("SIM-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        return credit;
    }
}
