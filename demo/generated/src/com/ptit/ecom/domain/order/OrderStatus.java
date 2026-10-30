package com.ptit.ecom.domain.order;

/**
 * States of the order state machine (slide 03).
 * Generated from the 4.4 design model (tools/model.py).
 */
public enum OrderStatus {
    PLACED, PROCESSING, SHIPPED, DELIVERED, CANCELLED
}
