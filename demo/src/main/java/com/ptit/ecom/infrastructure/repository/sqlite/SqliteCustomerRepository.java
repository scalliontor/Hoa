package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.customer.Address;
import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.customer.CustomerNew;
import com.ptit.ecom.domain.customer.CustomerVIP;
import com.ptit.ecom.domain.customer.FullName;
import com.ptit.ecom.infrastructure.repository.CustomerRepository;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * CustomerRepository implemented with SQLite (slide A05: Repository).
 * Reads the customer, customer_vip, customer_new and address tables into domain objects.
 */
public class SqliteCustomerRepository implements CustomerRepository {
    private Database database;

    public SqliteCustomerRepository(Database database) {
        this.database = database;
    }

    @Override
    public Customer findById(String customerId) {
        String sql = "SELECT customer_id, first_name, middle_name, last_name, email, phone, date_of_birth "
                + "FROM customer WHERE customer_id = ?";
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, customerId);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) return null;
                Customer customer = newCustomer(connection, customerId);
                customer.setCustomerId(customerId);
                customer.setEmail(row.getString("email"));
                customer.setPhone(row.getString("phone"));
                String birth = row.getString("date_of_birth");
                customer.setDateOfBirth(birth == null ? null : LocalDate.parse(birth));
                customer.setFullName(fullName(row));
                loadAddresses(connection, customer);
                return customer;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read customer " + customerId, e);
        }
    }

    @Override
    public List<Customer> allCustomers() {
        List<Customer> customers = new ArrayList<>();
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT customer_id FROM customer ORDER BY customer_id");
             ResultSet rows = statement.executeQuery()) {
            while (rows.next()) customers.add(findById(rows.getString("customer_id")));
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read the customer list", e);
        }
        return customers;
    }

    /** The customer_vip / customer_new rows decide which subclass is created (inheritance, section 4.2). */
    private Customer newCustomer(Connection connection, String customerId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT vip_level, discount_rate, reward_points FROM customer_vip WHERE customer_id = ?")) {
            statement.setString(1, customerId);
            try (ResultSet row = statement.executeQuery()) {
                if (row.next()) {
                    CustomerVIP vip = new CustomerVIP();
                    vip.setVipLevel(row.getInt("vip_level"));
                    vip.setDiscountRate(row.getBigDecimal("discount_rate"));
                    vip.setRewardPoints(row.getInt("reward_points"));
                    return vip;
                }
            }
        }
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT registered_date, welcome_voucher FROM customer_new WHERE customer_id = ?")) {
            statement.setString(1, customerId);
            try (ResultSet row = statement.executeQuery()) {
                if (row.next()) {
                    CustomerNew fresh = new CustomerNew();
                    fresh.setRegisteredDate(LocalDate.parse(row.getString("registered_date")));
                    fresh.setWelcomeVoucher(row.getString("welcome_voucher"));
                    return fresh;
                }
            }
        }
        return new Customer();
    }

    private FullName fullName(ResultSet row) throws SQLException {
        FullName name = new FullName();
        name.setFirstName(row.getString("first_name"));
        name.setMiddleName(row.getString("middle_name"));
        name.setLastName(row.getString("last_name"));
        return name;
    }

    private void loadAddresses(Connection connection, Customer customer) throws SQLException {
        String sql = "SELECT address_id, house_number, street, district, city FROM address "
                + "WHERE customer_id = ? ORDER BY address_id";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, customer.getCustomerId());
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    Address address = new Address();
                    address.setAddressId(row.getString("address_id"));
                    address.setHouseNumber(row.getString("house_number"));
                    address.setStreet(row.getString("street"));
                    address.setDistrict(row.getString("district"));
                    address.setCity(row.getString("city"));
                    customer.addAddress(address);
                }
            }
        }
    }
}
