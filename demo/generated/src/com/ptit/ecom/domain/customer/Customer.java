package com.ptit.ecom.domain.customer;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Domain class Customer, owner of the cart and the orders (slide A03).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Customer {
    private String customerId;
    private String email;
    private String phone;
    private LocalDate dateOfBirth;
    private FullName fullName;
    private List<Address> addresses = new ArrayList<>();

    public String getDisplayName() {
        return fullName.getDisplayName();
    }

    public BigDecimal getDiscountRate() {
        return BigDecimal.ZERO;
    }

    public void addAddress(Address address) {
        addresses.add(address);
    }

    public Address findAddress(String addressId) {
        for (Address address : addresses) {
            if (address.getAddressId().equals(addressId)) return address;
        }
        throw new IllegalArgumentException("Address " + addressId + " does not belong to customer " + customerId);
    }

    public String getCustomerId() {
        return customerId;
    }

    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public LocalDate getDateOfBirth() {
        return dateOfBirth;
    }

    public void setDateOfBirth(LocalDate dateOfBirth) {
        this.dateOfBirth = dateOfBirth;
    }

    public FullName getFullName() {
        return fullName;
    }

    public void setFullName(FullName fullName) {
        this.fullName = fullName;
    }

    public List<Address> getAddresses() {
        return addresses;
    }
}
