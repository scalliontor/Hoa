package com.ptit.ecom.presentation.web;

import java.util.Map;

/**
 * Demo login session: the customer id always comes from the session (NFR01).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class SessionManager {
    private Map<String, String> sessions;

    public String login(String customerId) {
        throw new UnsupportedOperationException("TODO: login");
    }

    public String customerOf(String token) {
        throw new UnsupportedOperationException("TODO: customerOf");
    }

    public boolean isAdmin(String token) {
        throw new UnsupportedOperationException("TODO: isAdmin");
    }
}
