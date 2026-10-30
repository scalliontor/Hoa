package com.ptit.ecom.domain.order;

import com.ptit.ecom.domain.customer.Address;
import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Delivery data of one order (Kiem tra 01).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Shipping {
    private String shippingId;
    private String carrier;
    private String trackingNumber;
    private BigDecimal shippingFee;
    private ShippingStatus status;
    private LocalDate deliveredDate;
    private Address address;

    public void updateStatus(ShippingStatus newStatus) {
        status = newStatus;
    }

    public void markDelivered(LocalDate date) {
        status = ShippingStatus.DELIVERED;
        deliveredDate = date;
    }

    public String getShippingId() {
        return shippingId;
    }

    public void setShippingId(String shippingId) {
        this.shippingId = shippingId;
    }

    public String getCarrier() {
        return carrier;
    }

    public void setCarrier(String carrier) {
        this.carrier = carrier;
    }

    public String getTrackingNumber() {
        return trackingNumber;
    }

    public void setTrackingNumber(String trackingNumber) {
        this.trackingNumber = trackingNumber;
    }

    public BigDecimal getShippingFee() {
        return shippingFee;
    }

    public void setShippingFee(BigDecimal shippingFee) {
        this.shippingFee = shippingFee;
    }

    public ShippingStatus getStatus() {
        return status;
    }

    public void setStatus(ShippingStatus status) {
        this.status = status;
    }

    public LocalDate getDeliveredDate() {
        return deliveredDate;
    }

    public void setDeliveredDate(LocalDate deliveredDate) {
        this.deliveredDate = deliveredDate;
    }

    public Address getAddress() {
        return address;
    }

    public void setAddress(Address address) {
        this.address = address;
    }
}
