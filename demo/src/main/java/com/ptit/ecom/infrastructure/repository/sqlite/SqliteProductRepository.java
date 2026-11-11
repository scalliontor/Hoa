package com.ptit.ecom.infrastructure.repository.sqlite;

import com.ptit.ecom.domain.product.Artist;
import com.ptit.ecom.domain.product.Category;
import com.ptit.ecom.domain.product.DetailKind;
import com.ptit.ecom.domain.product.Frame;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.ProductRepository;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * ProductRepository implemented with SQLite (slide A06: Product Database).
 * Table product keeps the common part; painting / frame keep the subclass part (inheritance, section 4.2).
 * The category of a product names the detail table that holds that part (category.detail_kind).
 */
public class SqliteProductRepository implements ProductRepository {
    /** Read by column number, because product and category both have name and description. */
    private static final String PRODUCT_ROWS = "SELECT category.category_id, category.name, category.detail_kind, "
            + "category.description, product.product_id, product.name, product.price, product.stock_quantity, "
            + "product.image_url, product.description FROM product "
            + "JOIN category ON category.category_id = product.category_id";
    private Database database;

    public SqliteProductRepository(Database database) {
        this.database = database;
    }

    /** all_products() of slide A06. */
    @Override
    public List<Product> allProducts() {
        List<Product> products = new ArrayList<>();
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(
                     PRODUCT_ROWS + " ORDER BY category.detail_kind DESC, product.product_id");
             ResultSet rows = statement.executeQuery()) {
            while (rows.next()) products.add(toProduct(connection, rows));
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read the catalogue", e);
        }
        return products;
    }

    @Override
    public Product findById(String productId) {
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(
                     PRODUCT_ROWS + " WHERE product.product_id = ?")) {
            statement.setString(1, productId);
            try (ResultSet row = statement.executeQuery()) {
                return row.next() ? toProduct(connection, row) : null;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot read product " + productId, e);
        }
    }

    /** Decreases only when enough stock is left, so two buyers at once cannot make stock negative. */
    @Override
    public void decreaseStock(String productId, int quantity) {
        String sql = "UPDATE product SET stock_quantity = stock_quantity - ? "
                + "WHERE product_id = ? AND stock_quantity >= ?";
        try (Connection connection = database.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setInt(1, quantity);
            statement.setString(2, productId);
            statement.setInt(3, quantity);
            if (statement.executeUpdate() != 1) throw new IllegalStateException("Not enough stock: " + productId);
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot update the stock of " + productId, e);
        }
    }

    /** Inserts a new product, or updates the price, stock and description of an existing one. */
    @Override
    public void save(Product product) {
        try (Connection connection = database.getConnection()) {
            connection.setAutoCommit(false);
            if (exists(connection, product.getProductId())) updateProduct(connection, product);
            else insertProduct(connection, product);
            connection.commit();
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot save product " + product.getProductId(), e);
        }
    }

    private Product toProduct(Connection connection, ResultSet row) throws SQLException {
        Category category = toCategory(row);
        String productId = row.getString(5);
        Product product = switch (category.getDetailKind()) {
            case PAINTING -> loadPainting(connection, productId);
            case FRAME -> loadFrame(connection, productId);
        };
        product.setCategory(category);
        product.setProductId(productId);
        product.setName(row.getString(6));
        product.setPrice(row.getBigDecimal(7));
        product.setStockQuantity(row.getInt(8));
        product.setImageUrl(row.getString(9));
        product.setDescription(row.getString(10));
        return product;
    }

    /** category_id, name, detail_kind and description in the first four columns. */
    private static Category toCategory(ResultSet row) throws SQLException {
        Category category = new Category();
        category.setCategoryId(row.getString(1));
        category.setName(row.getString(2));
        category.setDetailKind(DetailKind.valueOf(row.getString(3)));
        category.setDescription(row.getString(4));
        return category;
    }

    /** The stored category, not the caller's copy, decides which products it accepts. */
    private Category findCategory(Connection connection, String categoryId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT category_id, name, detail_kind, description FROM category WHERE category_id = ?")) {
            statement.setString(1, categoryId);
            try (ResultSet row = statement.executeQuery()) {
                return row.next() ? toCategory(row) : null;
            }
        }
    }

    private Painting loadPainting(Connection connection, String productId) throws SQLException {
        String sql = "SELECT painting.style, painting.subject, painting.dominant_color, painting.medium, "
                + "painting.year_created, painting.width_cm, painting.height_cm, artist.artist_id, artist.name, "
                + "artist.nationality, artist.life_years FROM painting "
                + "JOIN artist ON artist.artist_id = painting.artist_id WHERE painting.product_id = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, productId);
            try (ResultSet row = statement.executeQuery()) {
                row.next();
                Painting painting = new Painting();
                painting.setStyle(row.getString("style"));
                painting.setSubject(row.getString("subject"));
                painting.setDominantColor(row.getString("dominant_color"));
                painting.setMedium(row.getString("medium"));
                painting.setYearCreated(row.getInt("year_created"));
                painting.setWidthCm(row.getInt("width_cm"));
                painting.setHeightCm(row.getInt("height_cm"));
                Artist artist = new Artist();
                artist.setArtistId(row.getString("artist_id"));
                artist.setName(row.getString("name"));
                artist.setNationality(row.getString("nationality"));
                artist.setLifeYears(row.getString("life_years"));
                painting.setArtist(artist);
                return painting;
            }
        }
    }

    private Frame loadFrame(Connection connection, String productId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT material, color, size_label FROM frame WHERE product_id = ?")) {
            statement.setString(1, productId);
            try (ResultSet row = statement.executeQuery()) {
                row.next();
                Frame frame = new Frame();
                frame.setMaterial(row.getString("material"));
                frame.setColor(row.getString("color"));
                frame.setSizeLabel(row.getString("size_label"));
                return frame;
            }
        }
    }

    private boolean exists(Connection connection, String productId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "SELECT product_id FROM product WHERE product_id = ?")) {
            statement.setString(1, productId);
            try (ResultSet row = statement.executeQuery()) {
                return row.next();
            }
        }
    }

    private void updateProduct(Connection connection, Product product) throws SQLException {
        String sql = "UPDATE product SET name = ?, price = ?, stock_quantity = ?, image_url = ?, description = ? "
                + "WHERE product_id = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, product.getName());
            statement.setBigDecimal(2, product.getPrice());
            statement.setInt(3, product.getStockQuantity());
            statement.setString(4, product.getImageUrl());
            statement.setString(5, product.getDescription());
            statement.setString(6, product.getProductId());
            statement.executeUpdate();
        }
    }

    private void insertProduct(Connection connection, Product product) throws SQLException {
        String categoryId = product.getCategory() == null ? null : product.getCategory().getCategoryId();
        Category category = findCategory(connection, categoryId);
        if (category == null || !category.accepts(product)) {
            throw new IllegalArgumentException(String.format("Product %s is a %s and cannot go in category %s",
                    product.getProductId(), product.getDetailKind(), categoryId));
        }
        product.setCategory(category);
        String sql = "INSERT INTO product (product_id, category_id, name, price, stock_quantity, image_url, "
                + "description) VALUES (?, ?, ?, ?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, product.getProductId());
            statement.setString(2, category.getCategoryId());
            statement.setString(3, product.getName());
            statement.setBigDecimal(4, product.getPrice());
            statement.setInt(5, product.getStockQuantity());
            statement.setString(6, product.getImageUrl());
            statement.setString(7, product.getDescription());
            statement.executeUpdate();
        }
        if (product instanceof Painting) insertPainting(connection, (Painting) product);
        if (product instanceof Frame) insertFrame(connection, (Frame) product);
    }

    private void insertPainting(Connection connection, Painting painting) throws SQLException {
        insertArtistIfNew(connection, painting.getArtist());
        String sql = "INSERT INTO painting (product_id, artist_id, style, subject, dominant_color, medium, "
                + "year_created, width_cm, height_cm) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, painting.getProductId());
            statement.setString(2, painting.getArtist().getArtistId());
            statement.setString(3, painting.getStyle());
            statement.setString(4, painting.getSubject());
            statement.setString(5, painting.getDominantColor());
            statement.setString(6, painting.getMedium());
            statement.setInt(7, painting.getYearCreated());
            statement.setInt(8, painting.getWidthCm());
            statement.setInt(9, painting.getHeightCm());
            statement.executeUpdate();
        }
        insertFeature(connection, painting);
    }

    /** Feature vector of a new painting, same formula as VectorIndex (table product_feature). */
    private void insertFeature(Connection connection, Painting painting) throws SQLException {
        double[] vector = VectorIndex.toVector(painting.getStyle(), painting.getSubject(), painting.getDominantColor());
        ByteBuffer bytes = ByteBuffer.allocate(4 * vector.length).order(ByteOrder.LITTLE_ENDIAN);
        for (double value : vector) bytes.putFloat((float) value);
        String sql = "INSERT INTO product_feature (product_id, model_version, feature_vector, updated_at) "
                + "VALUES (?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, painting.getProductId());
            statement.setString(2, "style-subject-color/v1");
            statement.setBytes(3, bytes.array());
            statement.setString(4, LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            statement.executeUpdate();
        }
    }

    private void insertArtistIfNew(Connection connection, Artist artist) throws SQLException {
        try (PreparedStatement check = connection.prepareStatement(
                "SELECT artist_id FROM artist WHERE artist_id = ?")) {
            check.setString(1, artist.getArtistId());
            try (ResultSet row = check.executeQuery()) {
                if (row.next()) return;
            }
        }
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO artist (artist_id, name, nationality, life_years) VALUES (?, ?, ?, ?)")) {
            statement.setString(1, artist.getArtistId());
            statement.setString(2, artist.getName());
            statement.setString(3, artist.getNationality());
            statement.setString(4, artist.getLifeYears());
            statement.executeUpdate();
        }
    }

    private void insertFrame(Connection connection, Frame frame) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                "INSERT INTO frame (product_id, material, color, size_label) VALUES (?, ?, ?, ?)")) {
            statement.setString(1, frame.getProductId());
            statement.setString(2, frame.getMaterial());
            statement.setString(3, frame.getColor());
            statement.setString(4, frame.getSizeLabel());
            statement.executeUpdate();
        }
    }
}
