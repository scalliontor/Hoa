package com.ptit.ecom.presentation.web;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Demo login session: the customer id always comes from the session (NFR01).
 * The browser only holds a random token in a cookie; "ADMIN" is the administrator account.
 */
public class SessionManager {
    private Map<String, String> sessions = new ConcurrentHashMap<>();

    public String login(String customerId) {
        String token = UUID.randomUUID().toString();
        sessions.put(token, customerId);
        return token;
    }

    public String customerOf(String token) {
        return token == null ? null : sessions.get(token);
    }

    public boolean isAdmin(String token) {
        return "ADMIN".equals(customerOf(token));
    }
}
