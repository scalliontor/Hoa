package com.ptit.ecom.infrastructure.dao.jdbc;

import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.infrastructure.dao.CustomerDAO;
import javax.sql.DataSource;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class JdbcCustomerDAO implements CustomerDAO {
    private DataSource dataSource;

    public JdbcCustomerDAO(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public Customer findById(String customerId) {
        throw new UnsupportedOperationException("TODO: findById");
    }
}
