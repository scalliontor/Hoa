public class WebServer {
    // ...
    /** One line per endpoint: method + path -> controller call. */
    private Object route(HttpExchange exchange, String route) throws IOException {
        String[] path = exchange.getRequestURI().getPath().split("/");
        if (route.equals("POST /api/login")) return login(exchange);
        if (route.equals("GET /api/session")) return session(exchange);
        if (route.equals("GET /api/products")) return searchController.search("");
        if (route.equals("GET /api/search")) return searchController.search(query(exchange, "q"));
        if (route.equals("POST /api/voice/transcribe")) return transcript(exchange);
        if (route.equals("POST /api/search/voice")) return searchController.searchVoice(body(exchange, "transcript"));
        if (route.equals("POST /api/search/image")) return searchController.searchImage(image(exchange, "image"));
        if (route.equals("POST /api/search/multimodal")) {
            JsonObject json = json(exchange);
            return searchController.searchMultimodal(text(json, "text"), decodeImage(text(json, "image")));
        }
        if (route.equals("POST /api/room/describe")) return searchController.describeRoom(image(exchange, "image"));
        if (route.equals("POST /api/room/search")) return searchController.searchRoom(image(exchange, "image"));
        if (route.equals("POST /api/assistant")) {
            return assistantController.ask(customer(exchange), body(exchange, "message"));
        }
        if (route.startsWith("/api/admin", route.indexOf(' ') + 1)) return admin(exchange, route, path);
        return customerRoute(exchange, route, path);
    }
    // ...
    private String customer(HttpExchange exchange) {
        String account = sessionManager.customerOf(token(exchange));
        if (account == null || "ADMIN".equals(account)) throw new SecurityException("Please sign in as a customer");
        return account;
    }
    // ...
}
