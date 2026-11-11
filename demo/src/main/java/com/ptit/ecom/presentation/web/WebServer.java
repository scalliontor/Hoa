package com.ptit.ecom.presentation.web;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonParseException;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import com.google.gson.JsonSerializer;
import com.ptit.ecom.domain.cart.Cart;
import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.product.Artist;
import com.ptit.ecom.domain.product.Category;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.presentation.controller.AdminController;
import com.ptit.ecom.presentation.controller.AssistantController;
import com.ptit.ecom.presentation.controller.CartController;
import com.ptit.ecom.presentation.controller.CheckoutController;
import com.ptit.ecom.presentation.controller.OrderController;
import com.ptit.ecom.presentation.controller.SearchController;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Set;

/**
 * Web server of the Presentation layer: routes HTTP requests to controllers (slide A05).
 * JSON API under /api, static files (the browser views) from web/. No framework: the JDK HttpServer and Gson.
 */
public class WebServer {
    private static final Path WEB = Path.of("web").toAbsolutePath().normalize();
    private static final Set<String> ACCOUNTS = Set.of("C001", "C002", "ADMIN");
    private static final int MAX_IMAGE_BYTES = 5 * 1024 * 1024;
    private static final DateTimeFormatter DATE_TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");
    private static final Gson PLAIN = dateAware(new GsonBuilder()).disableHtmlEscaping().create();
    private static final Gson GSON = dateAware(new GsonBuilder()).disableHtmlEscaping()
            .registerTypeHierarchyAdapter(Product.class, (JsonSerializer<Product>) (product, type, context) -> {
                JsonObject json = PLAIN.toJsonTree(product, product.getClass()).getAsJsonObject();
                json.addProperty("kind", product.getDetailKind().name());
                return json;
            }).create();
    private int port;
    private SessionManager sessionManager;
    private SearchController searchController;
    private CartController cartController;
    private CheckoutController checkoutController;
    private OrderController orderController;
    private AssistantController assistantController;
    private AdminController adminController;
    private HttpServer server;

    public WebServer(int port, SessionManager sessionManager, SearchController searchController,
                     CartController cartController, CheckoutController checkoutController,
                     OrderController orderController, AssistantController assistantController,
                     AdminController adminController) {
        this.port = port;
        this.sessionManager = sessionManager;
        this.searchController = searchController;
        this.cartController = cartController;
        this.checkoutController = checkoutController;
        this.orderController = orderController;
        this.assistantController = assistantController;
        this.adminController = adminController;
    }

    public void start() {
        try {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        } catch (IOException e) {
            throw new IllegalStateException("Port " + port + " is busy", e);
        }
        server.createContext("/api/", this::handleApi);
        server.createContext("/", this::handleStatic);
        server.start();
    }

    public void stop() {
        if (server != null) server.stop(0);
    }

    // ------------------------------------------------------------------ API

    private void handleApi(HttpExchange exchange) throws IOException {
        try {
            Object result = route(exchange, exchange.getRequestMethod() + " " + exchange.getRequestURI().getPath());
            send(exchange, 200, GSON.toJson(result));
        } catch (SecurityException e) {
            send(exchange, 403, error(e.getMessage()));
        } catch (NoSuchElementException e) {
            send(exchange, 404, error(e.getMessage()));
        } catch (IllegalArgumentException e) {
            send(exchange, 400, error(e.getMessage()));
        } catch (JsonParseException e) {
            send(exchange, 400, error("The request body is not valid JSON"));
        } catch (UnavailableException e) {
            send(exchange, 503, error(e.getMessage()));
        } catch (IllegalStateException e) {
            send(exchange, 409, error(e.getMessage()));
        } catch (RuntimeException e) {
            send(exchange, 500, error("Unexpected error: " + e.getMessage()));
        }
    }

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

    private Object customerRoute(HttpExchange exchange, String route, String[] path) throws IOException {
        String customerId = customer(exchange);
        if (route.equals("GET /api/cart")) return cartController.viewCart(customerId);
        if (route.equals("POST /api/cart/items")) {
            JsonObject json = json(exchange);
            return cartController.addItem(customerId, text(json, "productId"), number(json, "quantity"));
        }
        if (route.equals("PUT /api/cart/items")) {
            JsonObject json = json(exchange);
            return cartController.updateQuantity(customerId, text(json, "productId"), number(json, "quantity"));
        }
        if (route.equals("DELETE /api/cart/items")) {
            return cartController.removeItem(customerId, query(exchange, "productId"));
        }
        if (route.equals("POST /api/checkout")) {
            JsonObject json = json(exchange);
            String cartId = cartController.viewCart(customerId).getCartId();
            return checkoutController.checkout(customerId, cartId, text(json, "addressId"), text(json, "paymentMethod"));
        }
        if (route.equals("POST /api/addresses")) {
            JsonObject json = json(exchange);
            return checkoutController.addAddress(customerId, text(json, "houseNumber"), text(json, "street"),
                    text(json, "district"), text(json, "city"));
        }
        if (route.equals("GET /api/orders")) return orderController.listOrders(customerId);
        if (route.startsWith("GET /api/orders/")) return orderController.viewOrder(customerId, path[3]);
        if (route.startsWith("POST /api/orders/") && route.endsWith("/cancel")) {
            orderController.cancelOrder(customerId, path[3]);
            return orderController.viewOrder(customerId, path[3]);
        }
        throw new NoSuchElementException("Unknown endpoint " + route);
    }

    /** UC12 and UC13: only the administrator session may call these. */
    private Object admin(HttpExchange exchange, String route, String[] path) throws IOException {
        if (!sessionManager.isAdmin(token(exchange))) throw new SecurityException("Administrator only");
        if (route.equals("GET /api/admin/products")) return adminController.listProducts();
        if (route.startsWith("PUT /api/admin/products/")) {
            JsonObject json = json(exchange);
            return adminController.updateProduct(path[4], money(json, "price"), number(json, "stockQuantity"));
        }
        if (route.equals("POST /api/admin/paintings")) return adminController.addPainting(painting(json(exchange)));
        if (route.equals("GET /api/admin/orders")) return adminController.listAllOrders();
        if (route.startsWith("PUT /api/admin/orders/")) {
            return adminController.updateOrderStatus(path[4], body(exchange, "status"));
        }
        throw new NoSuchElementException("Unknown endpoint " + route);
    }

    private Object login(HttpExchange exchange) throws IOException {
        String account = body(exchange, "customerId");
        if (!ACCOUNTS.contains(account)) throw new IllegalArgumentException("Unknown demo account");
        exchange.getResponseHeaders().add("Set-Cookie",
                "hoa_session=" + sessionManager.login(account) + "; Path=/; HttpOnly; SameSite=Lax");
        return Map.of("customerId", account);
    }

    /** Who is signed in; customer details come through the cart (Cart owned by Customer). */
    private Object session(HttpExchange exchange) {
        String account = sessionManager.customerOf(token(exchange));
        Map<String, Object> session = new LinkedHashMap<>();
        session.put("customerId", account);
        session.put("admin", "ADMIN".equals(account));
        if (account != null && !"ADMIN".equals(account)) {
            Cart cart = cartController.viewCart(account);
            Customer owner = cart.getOwner();
            session.put("name", owner.getDisplayName());
            session.put("discountRate", owner.getDiscountRate());
            session.put("addresses", owner.getAddresses());
            session.put("cartCount", cart.getItems().size());
        }
        return session;
    }

    /** The transcript; "" with a message when no words were heard; HTTP 503 when Whisper cannot be reached. */
    private Object transcript(HttpExchange exchange) throws IOException {
        String text = searchController.transcribe(exchange.getRequestBody().readAllBytes());
        if (text == null) {
            throw new UnavailableException("Voice search is unavailable right now. Please type your request.");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("transcript", text);
        if (text.isEmpty()) result.put("error", "We couldn't hear you. Please try again or type your request.");
        return result;
    }

    private static Painting painting(JsonObject json) {
        Artist artist = new Artist();
        artist.setArtistId(text(json, "artistId"));
        artist.setName(text(json, "artistName"));
        Category category = new Category();
        category.setCategoryId(text(json, "categoryId"));
        Painting painting = new Painting();
        painting.setCategory(category);
        painting.setName(text(json, "name"));
        painting.setArtist(artist);
        painting.setPrice(money(json, "price"));
        painting.setStockQuantity(number(json, "stockQuantity"));
        painting.setStyle(text(json, "style"));
        painting.setSubject(text(json, "subject"));
        painting.setDominantColor(text(json, "dominantColor"));
        painting.setMedium(text(json, "medium"));
        painting.setYearCreated(number(json, "yearCreated"));
        painting.setWidthCm(number(json, "widthCm"));
        painting.setHeightCm(number(json, "heightCm"));
        painting.setImageUrl(text(json, "imageUrl"));
        painting.setDescription("Museum-quality " + painting.getMedium().toLowerCase() + " of the "
                + painting.getYearCreated() + " original by " + artist.getName() + ".");
        return painting;
    }

    // ------------------------------------------------------- request helpers

    private String customer(HttpExchange exchange) {
        String account = sessionManager.customerOf(token(exchange));
        if (account == null || "ADMIN".equals(account)) throw new SecurityException("Please sign in as a customer");
        return account;
    }

    private static String token(HttpExchange exchange) {
        String cookies = exchange.getRequestHeaders().getFirst("Cookie");
        if (cookies == null) return null;
        for (String cookie : cookies.split(";")) {
            String[] pair = cookie.trim().split("=", 2);
            if (pair.length == 2 && pair[0].equals("hoa_session")) return pair[1];
        }
        return null;
    }

    private static JsonObject json(HttpExchange exchange) throws IOException {
        String text = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        return text.isBlank() ? new JsonObject() : JsonParser.parseString(text).getAsJsonObject();
    }

    private static String body(HttpExchange exchange, String key) throws IOException {
        return text(json(exchange), key);
    }

    private static String text(JsonObject json, String key) {
        return field(json, key).getAsString();
    }

    private static int number(JsonObject json, String key) {
        return field(json, key).getAsInt();
    }

    private static BigDecimal money(JsonObject json, String key) {
        return field(json, key).getAsBigDecimal();
    }

    private static JsonElement field(JsonObject json, String key) {
        if (!json.has(key) || json.get(key).isJsonNull()) throw new IllegalArgumentException("Missing field " + key);
        return json.get(key);
    }

    private static String query(HttpExchange exchange, String key) {
        String raw = exchange.getRequestURI().getRawQuery();
        if (raw == null) return "";
        for (String pair : raw.split("&")) {
            String[] parts = pair.split("=", 2);
            if (parts[0].equals(key)) {
                return parts.length < 2 ? "" : java.net.URLDecoder.decode(parts[1], StandardCharsets.UTF_8);
            }
        }
        return "";
    }

    private static byte[] image(HttpExchange exchange, String key) throws IOException {
        return decodeImage(body(exchange, key));
    }

    /** NFR03: only JPEG, PNG or WebP up to 5 MB; the type is checked on the bytes, not on the name. */
    private static byte[] decodeImage(String dataUrl) {
        if (dataUrl == null || !dataUrl.matches("(?s)^data:image/(jpeg|png|webp);base64,.*")) {
            throw new IllegalArgumentException("Please upload a JPEG, PNG or WebP image");
        }
        byte[] bytes = Base64.getDecoder().decode(dataUrl.substring(dataUrl.indexOf(',') + 1));
        if (bytes.length > MAX_IMAGE_BYTES) throw new IllegalArgumentException("The image is larger than 5 MB");
        boolean jpeg = bytes.length > 2 && bytes[0] == (byte) 0xFF && bytes[1] == (byte) 0xD8;
        boolean png = bytes.length > 3 && bytes[0] == (byte) 0x89 && bytes[1] == 'P' && bytes[2] == 'N';
        boolean webp = bytes.length > 11 && bytes[8] == 'W' && bytes[9] == 'E' && bytes[10] == 'B';
        if (!jpeg && !png && !webp) throw new IllegalArgumentException("The file is not a valid image");
        return bytes;
    }

    /** A service the request needs (the Whisper server) cannot be reached: HTTP 503. */
    private static class UnavailableException extends RuntimeException {
        UnavailableException(String message) {
            super(message);
        }
    }

    // ------------------------------------------------------------- responses

    private void handleStatic(HttpExchange exchange) throws IOException {
        String requested = exchange.getRequestURI().getPath();
        Path file = WEB.resolve(requested.equals("/") ? "index.html" : requested.substring(1)).normalize();
        if (!file.startsWith(WEB) || !Files.isRegularFile(file)) file = WEB.resolve("index.html");
        exchange.getResponseHeaders().set("Content-Type", contentType(file.toString()));
        exchange.sendResponseHeaders(200, Files.size(file));
        try (OutputStream out = exchange.getResponseBody()) {
            Files.copy(file, out);
        }
    }

    private static void send(HttpExchange exchange, int status, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(bytes);
        }
    }

    private static String error(String message) {
        return GSON.toJson(Map.of("error", String.valueOf(message)));
    }

    private static String contentType(String name) {
        if (name.endsWith(".html")) return "text/html; charset=utf-8";
        if (name.endsWith(".css")) return "text/css; charset=utf-8";
        if (name.endsWith(".js")) return "text/javascript; charset=utf-8";
        if (name.endsWith(".json")) return "application/json; charset=utf-8";
        if (name.endsWith(".png")) return "image/png";
        if (name.endsWith(".svg")) return "image/svg+xml";
        if (name.endsWith(".webp")) return "image/webp";
        return name.endsWith(".jpg") || name.endsWith(".jpeg") ? "image/jpeg" : "application/octet-stream";
    }

    /** java.time values become ISO strings and money keeps its plain decimal form. */
    private static GsonBuilder dateAware(GsonBuilder builder) {
        return builder
                .registerTypeAdapter(LocalDate.class, (JsonSerializer<LocalDate>)
                        (date, type, context) -> new JsonPrimitive(date.toString()))
                .registerTypeAdapter(LocalDateTime.class, (JsonSerializer<LocalDateTime>)
                        (time, type, context) -> new JsonPrimitive(time.format(DATE_TIME)))
                .registerTypeAdapter(BigDecimal.class, (JsonSerializer<BigDecimal>)
                        (money, type, context) -> new JsonPrimitive(money.stripTrailingZeros()));
    }
}
