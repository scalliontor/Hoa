package com.ptit.ecom.infrastructure.dao;

import com.ptit.ecom.domain.customer.Customer;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public interface CustomerDAO {
    Customer findById(String customerId);
}
