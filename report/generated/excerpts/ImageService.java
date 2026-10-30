public class ImageService {
    // ... (other members omitted)
    /** f(I): the photo becomes the same one-hot vector as the catalogue paintings. */
    public double[] embed(byte[] image) {
        Map<String, String> description = describe(image, "artwork");
        return VectorIndex.toVector(description.get("style"), description.get("subject"), description.get("color"));
    }

    /**
     * purpose is "artwork", "room", or "pick:" followed by candidate lines (Gemma then answers productId -> reason).
     * Gemma's answer is remembered, so the same photo and question call Gemma only once.
     */
    public Map<String, String> describe(byte[] image, String purpose) {
        String key = purpose + ":" + Arrays.hashCode(image);
        if (described.containsKey(key)) return described.get(key);
        try {
            Map<String, String> description = askGemma(image, prompt(purpose));
            description.put("ai", "gemma");
            if (described.size() > 50) described.clear();
            described.put(key, description);
            return description;
        } catch (RuntimeException e) {
            return readColorLocally(image);
        }
    }
}
