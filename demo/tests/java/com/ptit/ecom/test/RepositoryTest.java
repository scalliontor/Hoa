package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.freshDatabase;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.fails;
import static com.ptit.ecom.test.TestRunner.money;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.ptit.ecom.application.service.ProductService;
import com.ptit.ecom.domain.customer.Customer;
import com.ptit.ecom.domain.customer.CustomerNew;
import com.ptit.ecom.domain.customer.CustomerVIP;
import com.ptit.ecom.domain.order.Order;
import com.ptit.ecom.domain.payment.PayCredit;
import com.ptit.ecom.domain.product.Frame;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.sqlite.Database;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteCustomerRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteOrderRepository;
import com.ptit.ecom.infrastructure.repository.sqlite.SqliteProductRepository;
import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.List;

/** The SQLite repositories read and write the tables of section 4.2 (seed data of db/seed.sql). */
final class RepositoryTest {
    private RepositoryTest() {
    }

    static void run() {
        test("Seed: 32 paintings and 5 frames, prices in US dollars", () -> {
            List<Product> products = new SqliteProductRepository(freshDatabase()).allProducts();
            same(37, products.size(), "products");
            same(32L, products.stream().filter(p -> p instanceof Painting).count(), "paintings");
            same("P01", products.get(0).getProductId(), "first product");
            same("F01", products.get(32).getProductId(), "first product after the 32 paintings");
            for (Product product : products) {
                check(product.getPrice().compareTo(new BigDecimal("25")) >= 0
                        && product.getPrice().compareTo(new BigDecimal("180")) <= 0, "price of " + product.getName());
            }
        });
        test("The category picks the detail table: P01 is a Painting with its artist, F01 a Frame", () -> {
            SqliteProductRepository products = new SqliteProductRepository(freshDatabase());
            Product p01 = products.findById("P01");
            same(Painting.class, p01.getClass(), "P01 class");
            same("Fine-art prints", p01.getCategory().getName(), "P01 category");
            same("Claude Monet", ((Painting) p01).getArtist().getName(), "P01 artist");
            Product f01 = products.findById("F01");
            same(Frame.class, f01.getClass(), "F01 class");
            same("Frames", f01.getCategory().getName(), "F01 category");
            same("oak", ((Frame) f01).getMaterial(), "F01 material");
        });
        test("save refuses a frame in the prints category and writes nothing", () -> {
            Database database = freshDatabase();
            SqliteProductRepository products = new SqliteProductRepository(database);
            Frame frame = Fixtures.frame("F06", "40");
            frame.setCategory(products.findById("P01").getCategory());
            same(37, productRows(database), "product rows before");
            IllegalArgumentException error = fails(IllegalArgumentException.class, () -> products.save(frame));
            same("Product F06 is a FRAME and cannot go in category CAT-PRINTS", error.getMessage(), "message");
            same(37, productRows(database), "product rows after");
        });
        test("A customer is loaded as CustomerVIP or CustomerNew with name and addresses", () -> {
            SqliteCustomerRepository customers = new SqliteCustomerRepository(freshDatabase());
            Customer an = customers.findById("C001");
            check(an instanceof CustomerVIP, "C001 is VIP");
            same("Nguyen Minh An", an.getDisplayName(), "name");
            same(2, an.getAddresses().size(), "addresses");
            check(customers.findById("C002") instanceof CustomerNew, "C002 is new");
        });
        test("An order is read with its items, shipping and the PayCredit subclass", () -> {
            Order order = new SqliteOrderRepository(freshDatabase()).findOrder("20261001");
            same(2, order.getItems().size(), "items");
            same("GHN26102001", order.getShipping().getTrackingNumber(), "tracking number");
            check(order.getPayments().get(0) instanceof PayCredit, "card payment");
            money("107", order.getTotalAmount(), "total");
        });
        test("decreaseStock refuses to go below zero in the database", () -> {
            SqliteProductRepository products = new SqliteProductRepository(freshDatabase());
            int stock = products.findById("P03").getStockQuantity();
            fails(IllegalStateException.class, () -> products.decreaseStock("P03", stock + 1));
            products.decreaseStock("P03", stock);
            same(0, products.findById("P03").getStockQuantity(), "stock");
        });
        test("ProductService.addPainting stores the painting, a new artist and its feature vector (UC12)", () -> {
            Database database = freshDatabase();
            SqliteProductRepository products = new SqliteProductRepository(database);
            Painting painting = Fixtures.painting(null, "99", 4);
            painting.getArtist().setArtistId("A99");
            painting.getArtist().setName("Test Artist");
            painting.setMedium("Canvas print");
            painting.setYearCreated(1890);
            painting.setWidthCm(60);
            painting.setHeightCm(40);
            Painting saved = new ProductService(products).addPainting(painting);
            same("P33", saved.getProductId(), "next id");
            Painting loaded = (Painting) products.findById("P33");
            same("Test Artist", loaded.getArtist().getName(), "artist");
            same("Fine-art prints", loaded.getCategory().getName(), "category");
            try (Connection connection = database.getConnection(); Statement statement = connection.createStatement();
                 ResultSet row = statement.executeQuery(
                         "SELECT length(feature_vector) FROM product_feature WHERE product_id = 'P33'")) {
                check(row.next(), "feature row");
                same(28 * 4, row.getInt(1), "bytes of the float32 vector");
            }
        });
        test("ProductService refuses negative price or stock", () -> {
            ProductService service = new ProductService(new SqliteProductRepository(freshDatabase()));
            fails(IllegalArgumentException.class, () -> service.updatePriceAndStock("P01", new BigDecimal("-1"), 3));
            fails(IllegalArgumentException.class, () -> service.updatePriceAndStock("P01", new BigDecimal("10"), -3));
            money("59", service.updatePriceAndStock("P01", new BigDecimal("59"), 3).getPrice(), "new price");
        });
    }

    private static int productRows(Database database) throws Exception {
        try (Connection connection = database.getConnection(); Statement statement = connection.createStatement();
             ResultSet row = statement.executeQuery("SELECT count(*) FROM product")) {
            row.next();
            return row.getInt(1);
        }
    }
}
