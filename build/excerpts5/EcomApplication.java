public class EcomApplication {
    // ...
    public static void main(String[] args) throws IOException {
        Properties config = new Properties();
        try (Reader reader = Files.newBufferedReader(Path.of(args.length > 0 ? args[0] : "config/app.properties"))) {
            config.load(reader);
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
    // ...
}
