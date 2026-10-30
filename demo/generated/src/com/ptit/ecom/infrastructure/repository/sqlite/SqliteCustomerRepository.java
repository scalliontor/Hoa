package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.infrastructure.repository.CustomerRepository;
import java.util.List;

/**
 * CustomerRepository implemented with SQLite (slide A05: Repository).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class SqliteCustomerRepository implements CustomerRepository {
    private Database database;

    public SqliteCustomerRepository(Database database) {
        throw new UnsupportedOperationException("TODO: SqliteCustomerRepository");
    }

    @Override
    public Customer findById(String customerId) {
        throw new UnsupportedOperationException("TODO: findById");
    }

    @Override
    public List<Customer> allCustomers() {
        throw new UnsupportedOperationException("TODO: allCustomers");
    }
}
