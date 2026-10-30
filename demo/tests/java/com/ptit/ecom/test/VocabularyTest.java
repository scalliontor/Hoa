package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.freshDatabase;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.ptit.ecom.application.search.ImageService;
import com.ptit.ecom.application.search.QueryService;
import com.ptit.ecom.infrastructure.repository.sqlite.Database;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import com.ptit.ecom.test.Fixtures.FakeLlmClient;
import java.awt.Color;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The style / subject / colour lists are written in four places: tools/gen_sql.py (seed and feature vectors),
 * VectorIndex, the QueryService prompt and the ImageService prompts. This test keeps them identical.
 */
final class VocabularyTest {
    static final List<String> STYLES = List.of("Impressionism", "Post-Impressionism", "Ukiyo-e", "Art Nouveau",
            "Baroque", "Romanticism", "Expressionism", "Abstract", "Realism", "Naive art");
    static final List<String> SUBJECTS = List.of("landscape", "seascape", "flowers", "portrait", "still life",
            "cityscape", "everyday life", "abstract");
    static final List<String> COLORS = List.of("blue", "green", "yellow", "red", "orange", "brown", "white",
            "black", "purple", "pink");

    private VocabularyTest() {
    }

    static void run() {
        test("VectorIndex has one distinct dimension per style, subject and colour", () -> {
            Set<Integer> positions = new HashSet<>();
            for (String style : STYLES) positions.add(onlyOne(VectorIndex.toVector(style, null, null), style));
            for (String subject : SUBJECTS) positions.add(onlyOne(VectorIndex.toVector(null, subject, null), subject));
            for (String color : COLORS) positions.add(onlyOne(VectorIndex.toVector(null, null, color), color));
            same(28, positions.size(), "distinct dimensions");
        });
        test("The QueryService prompt lists the whole vocabulary", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().answer("{}");
            new QueryService(gemma).textQuery("anything");
            containsAll((String) gemma.conversations.get(0).get(0).get("content"), "query prompt");
        });
        test("Both ImageService prompts (artwork, room) list the whole vocabulary", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().answer("{}").answer("{}");
            ImageService images = new ImageService(gemma);
            images.describe(SearchTest.png(Color.BLUE), "artwork");
            images.describe(SearchTest.png(Color.BLUE), "room");
            for (int i = 0; i < 2; i++) {
                List<?> content = (List<?>) gemma.conversations.get(i).get(0).get("content");
                containsAll((String) ((Map<?, ?>) content.get(0)).get("text"), i == 0 ? "artwork prompt" : "room prompt");
            }
        });
        test("Every stored feature vector equals VectorIndex.toVector of its painting", () -> {
            Database database = freshDatabase();
            String sql = "SELECT painting.product_id, painting.style, painting.subject, painting.dominant_color, "
                    + "product_feature.model_version, product_feature.feature_vector FROM painting "
                    + "JOIN product_feature ON product_feature.product_id = painting.product_id";
            int rows = 0;
            try (Connection connection = database.getConnection(); Statement statement = connection.createStatement();
                 ResultSet row = statement.executeQuery(sql)) {
                while (row.next()) {
                    rows++;
                    String id = row.getString(1);
                    check(STYLES.contains(row.getString(2)) && SUBJECTS.contains(row.getString(3))
                            && COLORS.contains(row.getString(4)), "vocabulary of " + id);
                    same("style-subject-color/v1", row.getString(5), "model version of " + id);
                    ByteBuffer blob = ByteBuffer.wrap(row.getBytes(6)).order(ByteOrder.LITTLE_ENDIAN);
                    double[] expected = VectorIndex.toVector(row.getString(2), row.getString(3), row.getString(4));
                    for (double value : expected) same((float) value, blob.getFloat(), "vector of " + id);
                }
            }
            same(32, rows, "paintings with a feature vector");
        });
    }

    private static int onlyOne(double[] vector, String value) {
        int position = -1;
        for (int i = 0; i < vector.length; i++) {
            if (vector[i] == 1.0) {
                check(position < 0, value + " sets two dimensions");
                position = i;
            }
        }
        check(position >= 0, value + " is not in VectorIndex");
        return position;
    }

    private static void containsAll(String prompt, String what) {
        for (List<String> list : List.of(STYLES, SUBJECTS, COLORS)) {
            for (String value : list) check(prompt.contains(value), what + " misses " + value);
        }
    }
}
