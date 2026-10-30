package com.ptit.ecom.infrastructure.search;

import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Vector index with the cosine_similarity of slide A06 (Vector Index).
 * A painting is encoded as one-hot style + subject + colour, the same attributes Gemma 4 reads from a photo.
 */
public class VectorIndex {
    private static final String[] STYLES = {"Impressionism", "Post-Impressionism", "Ukiyo-e", "Art Nouveau", "Baroque",
            "Romanticism", "Expressionism", "Abstract", "Realism", "Naive art"};
    private static final String[] SUBJECTS = {"landscape", "seascape", "flowers", "portrait", "still life",
            "cityscape", "everyday life", "abstract"};
    private static final String[] COLORS = {"blue", "green", "yellow", "red", "orange", "brown", "white", "black",
            "purple", "pink"};
    private Map<String, double[]> productEmbeddings = new HashMap<>();

    /** Encodes every painting of the catalogue; frames have no picture to compare. */
    public void build(List<Product> products) {
        productEmbeddings.clear();
        for (Product product : products) {
            if (product instanceof Painting) productEmbeddings.put(product.getProductId(), embedProduct(product));
        }
    }

    public double[] embedProduct(Product product) {
        if (!(product instanceof Painting)) return toVector(null, null, null);
        Painting painting = (Painting) product;
        return toVector(painting.getStyle(), painting.getSubject(), painting.getDominantColor());
    }

    /** One-hot vector: [10 styles | 8 subjects | 10 colours]; an unknown value leaves its part at zero. */
    public static double[] toVector(String style, String subject, String color) {
        double[] vector = new double[STYLES.length + SUBJECTS.length + COLORS.length];
        mark(vector, 0, STYLES, style);
        mark(vector, STYLES.length, SUBJECTS, subject);
        mark(vector, STYLES.length + SUBJECTS.length, COLORS, color);
        return vector;
    }

    /** cosine_similarity(a, b) of slide A06. */
    public static double cosineSimilarity(double[] a, double[] b) {
        double numerator = 0, normA = 0, normB = 0;
        for (int i = 0; i < a.length; i++) {
            numerator += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }
        double denominator = Math.sqrt(normA) * Math.sqrt(normB);
        return denominator == 0 ? 0.0 : numerator / denominator;
    }

    /** The k products closest to the query vector, most similar first (similarity above zero only). */
    public Map<String, Double> nearest(double[] queryEmbedding, int k) {
        List<Map.Entry<String, Double>> scores = new ArrayList<>();
        for (Map.Entry<String, double[]> entry : productEmbeddings.entrySet()) {
            double score = cosineSimilarity(queryEmbedding, entry.getValue());
            if (score > 0) scores.add(Map.entry(entry.getKey(), score));
        }
        scores.sort((x, y) -> Double.compare(y.getValue(), x.getValue()));
        Map<String, Double> result = new LinkedHashMap<>();
        for (Map.Entry<String, Double> entry : scores.subList(0, Math.min(k, scores.size()))) {
            result.put(entry.getKey(), entry.getValue());
        }
        return result;
    }

    private static void mark(double[] vector, int offset, String[] vocabulary, String value) {
        if (value == null) return;
        for (int i = 0; i < vocabulary.length; i++) {
            if (vocabulary[i].equalsIgnoreCase(value.trim())) vector[offset + i] = 1.0;
        }
    }
}
