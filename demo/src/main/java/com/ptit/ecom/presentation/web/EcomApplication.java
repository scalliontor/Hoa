package com.ptit.ecom.presentation.web;

import com.ptit.ecom.application.search.ImageService;
import com.ptit.ecom.application.search.QueryService;
import com.ptit.ecom.application.search.RankingService;
import com.ptit.ecom.application.search.SearchService;
import com.ptit.ecom.application.search.SpeechService;
import com.ptit.ecom.application.service.AssistantService;
import com.ptit.ecom.application.service.CartService;
import com.ptit.ecom.application.service.CheckoutService;
import com.ptit.ecom.application.service.OrderService;
import com.ptit.ecom.application.service.ProductService;
import com.ptit.ecom.infrastructure.ai.GemmaClient;
import com.ptit.ecom.infrastructure.ai.LlmClient;
import com.ptit.ecom.infrastructure.ai.WhisperClient;
import com.ptit.ecom.infrastructure.repository.sqlite.Database;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteCartRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteCustomerRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteOrderRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteProductRepository;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import com.ptit.ecom.presentation.controller.AdminController;
import com.ptit.ecom.presentation.controller.AssistantController;
import com.ptit.ecom.presentation.controller.CartController;
import com.ptit.ecom.presentation.controller.CheckoutController;
import com.ptit.ecom.presentation.controller.OrderController;
import com.ptit.ecom.presentation.controller.SearchController;
import java.io.IOException;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/**
 * Entry point that wires the layers, like main.py in slide A06.
 * Infrastructure -> Application -> Presentation, each object created once (composition root).
 */
public class EcomApplication {

    public static void main(String[] args) throws IOException {
        Properties config = new Properties();
        try (Reader reader = Files.newBufferedReader(Path.of(args.length > 0 ? args[0] : "config/app.properties"))) {
            config.load(reader);
        }
        // Secrets such as gemma.apiKey live in config/app.local.properties, which is not in git.
        Path local = Path.of("config/app.local.properties");
        if (Files.exists(local)) {
            try (Reader reader = Files.newBufferedReader(local)) {
                config.load(reader);
            }
        }
        Files.createDirectories(Path.of("data"));
        Database database = new Database("jdbc:sqlite:" + config.getProperty("db.path"));
        database.initialize(Files.readString(Path.of("db/ecom_schema_sqlite.sql")), Files.readString(Path.of("db/seed.sql")));

        SqliteProductRepository products = new SqliteProductRepository(database);
        SqliteOrderRepository orders = new SqliteOrderRepository(database);
        SqliteCartRepository carts = new SqliteCartRepository(database);
        SqliteCustomerRepository customers = new SqliteCustomerRepository(database);
        LlmClient gemma = new GemmaClient(config.getProperty("gemma.baseUrl"), config.getProperty("gemma.apiKey"),
                config.getProperty("gemma.model"), Integer.parseInt(config.getProperty("gemma.timeoutSeconds")));
        WhisperClient whisper = new WhisperClient(config.getProperty("whisper.baseUrl"),
                config.getProperty("whisper.model"), Integer.parseInt(config.getProperty("whisper.timeoutSeconds")));

        RankingService ranking = new RankingService(Double.parseDouble(config.getProperty("ranking.alpha")),
                Double.parseDouble(config.getProperty("ranking.beta")), Double.parseDouble(config.getProperty("ranking.gamma")));
        SearchService search = new SearchService(products, new QueryService(gemma), new ImageService(gemma),
                new VectorIndex(), ranking);
        OrderService orderService = new OrderService(orders);

        int port = Integer.parseInt(config.getProperty("server.port"));
        WebServer server = new WebServer(port, new SessionManager(),
                new SearchController(search, new SpeechService(whisper)),
                new CartController(new CartService(carts, products)),
                new CheckoutController(new CheckoutService(carts, orders, products, customers)),
                new OrderController(orderService),
                new AssistantController(new AssistantService(gemma, search, orderService)),
                new AdminController(new ProductService(products), orderService));
        server.start();
        System.out.println("Họa. is running at http://127.0.0.1:" + port);
        System.out.println("Gemma 4: " + (gemma.isAvailable() ? "online" : "offline (keyword fallback)")
                + " | Whisper: " + (whisper.isAvailable() ? "online" : "offline (type instead)"));
    }
}
