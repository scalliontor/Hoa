package com.ptit.ecom.test;

import com.ptit.ecom.application.search.ImageService;
import com.ptit.ecom.application.search.QueryService;
import com.ptit.ecom.application.search.RankingService;
import com.ptit.ecom.application.search.SearchService;
import com.ptit.ecom.domain.customer.Address;
import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.product.Artist;
import com.ptit.ecom.domain.product.Category;
import com.ptit.ecom.domain.product.DetailKind;
import com.ptit.ecom.domain.product.Frame;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.infrastructure.ai.LlmClient;
import com.ptit.ecom.infrastructure.ai.LlmReply;
import com.ptit.ecom.infrastructure.ai.SpeechClient;
import com.ptit.ecom.infrastructure.ai.ToolCall;
import com.ptit.ecom.infrastructure.repository.sqlite.Database;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteProductRepository;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Map;

/** Test data and fakes: a fresh seeded SQLite file, products, and Gemma / Whisper stand-ins. */
final class Fixtures {
    private Fixtures() {
    }

    /** A new database file with the schema and seed data of db/ (run from the demo folder). */
    static Database freshDatabase() throws IOException {
        Path file = Files.createTempFile("hoa-test-", ".db");
        file.toFile().deleteOnExit();
        Files.delete(file);
        Database database = new Database("jdbc:sqlite:" + file);
        database.initialize(Files.readString(Path.of("db/ecom_schema_sqlite.sql")),
                Files.readString(Path.of("db/seed.sql")));
        return database;
    }

    static SearchService searchService(Database database, LlmClient gemma) {
        return new SearchService(new SqliteProductRepository(database), new QueryService(gemma),
                new ImageService(gemma), new VectorIndex(), new RankingService(0.45, 0.45, 0.10));
    }

    static Category category(String id, String name, DetailKind detailKind) {
        Category category = new Category();
        category.setCategoryId(id);
        category.setName(name);
        category.setDetailKind(detailKind);
        return category;
    }

    static Painting painting(String id, String price, int stock) {
        Artist artist = new Artist();
        artist.setArtistId("A01");
        artist.setName("Claude Monet");
        Painting painting = new Painting();
        painting.setProductId(id);
        painting.setCategory(category("CAT-PRINTS", "Fine-art prints", DetailKind.PAINTING));
        painting.setName("Painting " + id);
        painting.setPrice(new BigDecimal(price));
        painting.setStockQuantity(stock);
        painting.setStyle("Impressionism");
        painting.setSubject("landscape");
        painting.setDominantColor("blue");
        painting.setArtist(artist);
        return painting;
    }

    static Frame frame(String id, String price) {
        Frame frame = new Frame();
        frame.setProductId(id);
        frame.setCategory(category("CAT-FRAMES", "Frames", DetailKind.FRAME));
        frame.setName("Frame " + id);
        frame.setPrice(new BigDecimal(price));
        frame.setStockQuantity(10);
        frame.setMaterial("oak");
        frame.setColor("brown");
        return frame;
    }

    static Customer customer(String id, String addressId) {
        Address address = new Address();
        address.setAddressId(addressId);
        Customer customer = new Customer();
        customer.setCustomerId(id);
        customer.addAddress(address);
        return customer;
    }

    /** Gemma 4 stand-in: replies from a script, or throws like an unreachable server. */
    static final class FakeLlmClient implements LlmClient {
        final List<List<Map<String, Object>>> conversations = new ArrayList<>();
        final List<List<Map<String, Object>>> toolLists = new ArrayList<>();
        private final Deque<LlmReply> replies = new ArrayDeque<>();
        private final boolean online;

        private FakeLlmClient(boolean online) {
            this.online = online;
        }

        static FakeLlmClient offline() {
            return new FakeLlmClient(false);
        }

        static FakeLlmClient online() {
            return new FakeLlmClient(true);
        }

        FakeLlmClient answer(String content) {
            replies.add(new LlmReply(content, List.of()));
            return this;
        }

        FakeLlmClient callTool(String name, String arguments) {
            replies.add(new LlmReply("", List.of(new ToolCall("call-" + replies.size(), name, arguments))));
            return this;
        }

        @Override
        public LlmReply chat(List<Map<String, Object>> messages, List<Map<String, Object>> tools) {
            if (!online) throw new IllegalStateException("Gemma 4 is not reachable (test)");
            conversations.add(new ArrayList<>(messages));
            toolLists.add(tools);
            if (replies.isEmpty()) throw new IllegalStateException("No scripted reply left");
            return replies.poll();
        }

        @Override
        public boolean isAvailable() {
            return online;
        }
    }

    /** Whisper stand-in: returns the transcript, or throws like a stopped server when it is null. */
    static final class FakeSpeechClient implements SpeechClient {
        String transcript;
        String lastLanguage;

        FakeSpeechClient(String transcript) {
            this.transcript = transcript;
        }

        @Override
        public String transcribe(byte[] audio, String language) {
            lastLanguage = language;
            if (transcript == null) throw new IllegalStateException("Whisper server is not running (test)");
            return transcript;
        }

        @Override
        public boolean isAvailable() {
            return transcript != null;
        }
    }
}
