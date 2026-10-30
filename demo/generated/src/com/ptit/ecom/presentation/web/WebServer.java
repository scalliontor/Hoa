package com.ptit.ecom.presentation.web;

import com.ptit.ecom.presentation.controller.AdminController;
import com.ptit.ecom.presentation.controller.AssistantController;
import com.ptit.ecom.presentation.controller.CartController;
import com.ptit.ecom.presentation.controller.CheckoutController;
import com.ptit.ecom.presentation.controller.OrderController;
import com.ptit.ecom.presentation.controller.SearchController;

/**
 * Web server of the Presentation layer: routes HTTP requests to controllers (slide A05).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class WebServer {
    private int port;
    private SessionManager sessionManager;
    private SearchController searchController;
    private CartController cartController;
    private CheckoutController checkoutController;
    private OrderController orderController;
    private AssistantController assistantController;
    private AdminController adminController;

    public WebServer(int port, SessionManager sessionManager, SearchController searchController, CartController cartController, CheckoutController checkoutController, OrderController orderController, AssistantController assistantController, AdminController adminController) {
        throw new UnsupportedOperationException("TODO: WebServer");
    }

    public void start() {
        throw new UnsupportedOperationException("TODO: start");
    }

    public void stop() {
        throw new UnsupportedOperationException("TODO: stop");
    }
}
