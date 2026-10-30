public class VectorIndex {
    // ...
    /** One-hot vector: [10 styles | 8 subjects | 10 colours]; an unknown value leaves its part at zero. */
    public static double[] toVector(String style, String subject, String color) {
        double[] vector = new double[STYLES.length + SUBJECTS.length + COLORS.length];
        mark(vector, 0, STYLES, style);
        mark(vector, STYLES.length, SUBJECTS, subject);
        mark(vector, STYLES.length + SUBJECTS.length, COLORS, color);
        return vector;
    }
    // ...
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
    // ...
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
    // ...
}
