package com.ptit.ecom.domain.customer;

/**
 * Delivery address of a customer (Kiem tra 01).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Address {
    private String addressId;
    private String houseNumber;
    private String street;
    private String district;
    private String city;

    public String format() {
        return houseNumber + " " + street + ", " + district + ", " + city;
    }

    public String getAddressId() {
        return addressId;
    }

    public void setAddressId(String addressId) {
        this.addressId = addressId;
    }

    public String getHouseNumber() {
        return houseNumber;
    }

    public void setHouseNumber(String houseNumber) {
        this.houseNumber = houseNumber;
    }

    public String getStreet() {
        return street;
    }

    public void setStreet(String street) {
        this.street = street;
    }

    public String getDistrict() {
        return district;
    }

    public void setDistrict(String district) {
        this.district = district;
    }

    public String getCity() {
        return city;
    }

    public void setCity(String city) {
        this.city = city;
    }
}
