package com.ptit.ecom.infrastructure.repository;

import com.ptit.ecom.domain.customer.Address;
import com.ptit.ecom.domain.customer.Customer;
import java.util.List;

/**
 * Customer repository (slide A05: a Repository handles persistence).
 * Generated from the 4.4 design model (tools/model.py).
 */
public interface CustomerRepository {
    Customer findById(String customerId);

    List<Customer> allCustomers();

    Address saveAddress(String customerId, Address address);
}
