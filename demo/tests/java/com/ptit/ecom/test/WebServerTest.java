package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.freshDatabase;
import static com.ptit.ecom.test.Fixtures.searchService;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.ptit.ecom.application.search.SearchService;
import com.ptit.ecom.application.search.SpeechService;
import com.ptit.ecom.application.service.AssistantService;
import com.ptit.ecom.application.service.CartService;
import com.ptit.ecom.application.service.CheckoutService;
import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.application.service.ProductService;
import com.ptit.ecom.infrastructure.repository.sqlite.Database;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteCartRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteCustomerRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteOrderRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteProductRepository;
import com.ptit.ecom.presentation.controller.AdminController;
import com.ptit.ecom.presentation.controller.AssistantController;
import com.ptit.ecom.presentation.controller.CartController;
import com.ptit.ecom.presentation.controller.CheckoutController;
import com.ptit.ecom.presentation.controller.OrderController;
import com.ptit.ecom.presentation.controller.SearchController;
import com.ptit.ecom.presentation.web.SessionManager;
import com.ptit.ecom.presentation.web.WebServer;
import com.ptit.ecom.test.Fixtures.FakeLlmClient;
import com.ptit.ecom.test.Fixtures.FakeSpeechClient;
import java.awt.Color;
import java.net.ServerSocket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Base64;

/** The JSON API of WebServer: sessions, ownership (NFR01), upload checks (NFR03), administrator routes. */
final class WebServerTest {
    private static final HttpClient HTTP = HttpClient.newHttpClient();
    private static final FakeSpeechClient WHISPER = new FakeSpeechClient("blue landscape paintings.");
    private final String base;

    private WebServerTest(String base) {
        this.base = base;
    }

    static void run() throws Exception {
        int port;
        try (ServerSocket socket = new ServerSocket(0)) {
            port = socket.getLocalPort();
        }
        WebServer server = server(port);
        server.start();
        WebServerTest api = new WebServerTest("http://127.0.0.1:" + port);
        try {
            api.tests();
        } finally {
            server.stop();
        }
    }

    private void tests() {
        test("Customer routes need a signed-in customer (403)", () -> {
            same(403, call("GET", "/api/cart", null, null).statusCode(), "status without session");
        });
        test("Login sets an HttpOnly session cookie; the session names the customer", () -> {
            HttpResponse<String> login = call("POST", "/api/login", "{\"customerId\": \"C001\"}", null);
            String cookie = login.headers().firstValue("Set-Cookie").orElse("");
            check(cookie.startsWith("hoa_session=") && cookie.contains("HttpOnly"), "cookie " + cookie);
            check(call("GET", "/api/session", null, cookieOf(login)).body().contains("Nguyen Minh An"), "session");
        });
        test("Another customer's order answers 404 with the same message as a missing order (NFR01)", () -> {
            String c001 = login("C001");
            HttpResponse<String> other = call("GET", "/api/orders/20261003", null, c001);
            same(404, other.statusCode(), "status");
            same("{\"error\":\"Order 20261003 was not found in your account\"}", other.body(), "body");
            same(404, call("GET", "/api/orders/20261001", null, login("C002")).statusCode(), "C002 reading C001");
            same(200, call("GET", "/api/orders/20261001", null, c001).statusCode(), "own order");
        });
        test("A customerId in the request body is ignored: the session decides", () -> {
            HttpResponse<String> response = call("POST", "/api/checkout",
                    "{\"customerId\": \"C001\", \"addressId\": \"A003\", \"paymentMethod\": \"CASH\"}", login("C002"));
            same(409, response.statusCode(), "C002's own (empty) cart is used");
            check(response.body().contains("Your cart is empty"), response.body());
        });
        test("Uploads: only JPEG, PNG or WebP up to 5 MB, checked on the bytes (NFR03)", () -> {
            same(400, image("data:image/gif;base64,R0lGODlhAQABAAAAACw=").statusCode(), "GIF");
            String fake = Base64.getEncoder().encodeToString("not really a picture".getBytes());
            HttpResponse<String> notImage = image("data:image/jpeg;base64," + fake);
            same(400, notImage.statusCode(), "text renamed as JPEG");
            check(notImage.body().contains("not a valid image"), notImage.body());
            byte[] big = new byte[5 * 1024 * 1024 + 10];
            big[0] = (byte) 0x89;
            big[1] = 'P';
            big[2] = 'N';
            same(400, image("data:image/png;base64," + Base64.getEncoder().encodeToString(big)).statusCode(), "> 5 MB");
            String png = Base64.getEncoder().encodeToString(SearchTest.png(new Color(40, 90, 170)));
            same(200, image("data:image/png;base64," + png).statusCode(), "valid PNG");
        });
        test("Administrator routes need the ADMIN session", () -> {
            same(403, call("GET", "/api/admin/orders", null, login("C001")).statusCode(), "customer");
            HttpResponse<String> admin = call("GET", "/api/admin/orders", null, login("ADMIN"));
            same(200, admin.statusCode(), "administrator");
            check(admin.body().contains("20261003") && admin.body().contains("20261001"), "all orders");
        });
        test("Product JSON has the kind and the whole category", () -> {
            JsonArray results = JsonParser.parseString(call("GET", "/api/products", null, null).body()).getAsJsonArray();
            JsonObject p01 = product(results, "P01");
            same("PAINTING", p01.get("kind").getAsString(), "P01 kind");
            same("{\"categoryId\":\"CAT-PRINTS\",\"name\":\"Fine-art prints\",\"detailKind\":\"PAINTING\","
                    + "\"description\":\"Museum-quality prints of public-domain paintings\"}",
                    p01.get("category").toString(), "P01 category");
            JsonObject f01 = product(results, "F01");
            same("FRAME", f01.get("kind").getAsString(), "F01 kind");
            same("Frames", f01.getAsJsonObject("category").get("name").getAsString(), "F01 category name");
        });
        test("A new painting is saved only in a category that holds paintings (UC12)", () -> {
            String admin = login("ADMIN");
            String painting = "{\"name\": \"Almond Blossoms\", \"artistId\": \"A02\", \"artistName\": \"Vincent van Gogh\", "
                    + "\"style\": \"Post-Impressionism\", \"subject\": \"flowers\", \"dominantColor\": \"blue\", "
                    + "\"medium\": \"Canvas print\", \"yearCreated\": 1890, \"widthCm\": 92, \"heightCm\": 73, "
                    + "\"price\": 99, \"stockQuantity\": 5, \"imageUrl\": \"/img/P06.jpg\", \"categoryId\": \"%s\"}";
            HttpResponse<String> frames = call("POST", "/api/admin/paintings", String.format(painting, "CAT-FRAMES"), admin);
            same(400, frames.statusCode(), "painting in Frames");
            same("{\"error\":\"Product P33 is a PAINTING and cannot go in category CAT-FRAMES\"}", frames.body(), "error");
            HttpResponse<String> prints = call("POST", "/api/admin/paintings", String.format(painting, "CAT-PRINTS"), admin);
            same(200, prints.statusCode(), "painting in Fine-art prints");
            JsonObject saved = JsonParser.parseString(prints.body()).getAsJsonObject();
            same("P33", saved.get("productId").getAsString(), "new id");
            same("Fine-art prints", saved.getAsJsonObject("category").get("name").getAsString(), "category");
        });
        test("Voice: transcript to correct; nothing heard (200, empty); Whisper down (503)", () -> {
            HttpRequest request = HttpRequest.newBuilder(URI.create(base + "/api/voice/transcribe"))
                    .POST(HttpRequest.BodyPublishers.ofByteArray(new byte[] {1, 2, 3, 4})).build();
            same("{\"transcript\":\"blue landscape paintings\"}",
                    HTTP.send(request, HttpResponse.BodyHandlers.ofString()).body(), "transcript");
            WHISPER.transcript = "";
            HttpResponse<String> silence = HTTP.send(request, HttpResponse.BodyHandlers.ofString());
            same(200, silence.statusCode(), "nothing heard");
            check(silence.body().startsWith("{\"transcript\":\"\",\"error\":\"We couldn't hear you"), silence.body());
            WHISPER.transcript = null;
            HttpResponse<String> down = HTTP.send(request, HttpResponse.BodyHandlers.ofString());
            same(503, down.statusCode(), "Whisper down");
            check(down.body().contains("Voice search is unavailable"), down.body());
            WHISPER.transcript = "blue landscape paintings.";
        });
    }

    private static JsonObject product(JsonArray results, String productId) {
        for (JsonElement result : results) {
            JsonObject product = result.getAsJsonObject().getAsJsonObject("product");
            if (product.get("productId").getAsString().equals(productId)) return product;
        }
        throw new AssertionError(productId + " is not in the catalogue");
    }

    private HttpResponse<String> image(String dataUrl) throws Exception {
        return call("POST", "/api/search/image", "{\"image\": \"" + dataUrl + "\"}", null);
    }

    private String login(String account) throws Exception {
        return cookieOf(call("POST", "/api/login", "{\"customerId\": \"" + account + "\"}", null));
    }

    private static String cookieOf(HttpResponse<String> response) {
        return response.headers().firstValue("Set-Cookie").orElse("").split(";")[0];
    }

    private HttpResponse<String> call(String method, String path, String json, String cookie) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(base + path)).method(method,
                json == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(json));
        if (cookie != null) request.header("Cookie", cookie);
        return HTTP.send(request.build(), HttpResponse.BodyHandlers.ofString());
    }

    /** The same wiring as EcomApplication, with a fresh database, Gemma offline and a fake Whisper. */
    private static WebServer server(int port) throws Exception {
        Database database = freshDatabase();
        SqliteProductRepository products = new SqliteProductRepository(database);
        SqliteOrderRepository orders = new SqliteOrderRepository(database);
        SqliteCartRepository carts = new SqliteCartRepository(database);
        FakeLlmClient gemma = FakeLlmClient.offline();
        SearchService search = searchService(database, gemma);
        OrderService orderService = new OrderService(orders);
        return new WebServer(port, new SessionManager(),
                new SearchController(search, new SpeechService(WHISPER)),
                new CartController(new CartService(carts, products)),
                new CheckoutController(new CheckoutService(carts, orders, products, new SqliteCustomerRepository(database))),
                new OrderController(orderService),
                new AssistantController(new AssistantService(gemma, search, orderService)),
                new AdminController(new ProductService(products), orderService));
    }
}
