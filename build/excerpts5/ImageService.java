public class ImageService {
    // ...
    /** f(I): the photo becomes the same one-hot vector as the catalogue paintings. */
    public double[] embed(byte[] image) {
        Map<String, String> description = describe(image, "artwork");
        return VectorIndex.toVector(description.get("style"), description.get("subject"), description.get("color"));
    }
    // ...
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
    // ...
    private Map<String, String> askGemma(byte[] image, String prompt) {
        String dataUri = "data:" + mimeType(image) + ";base64," + Base64.getEncoder().encodeToString(image);
        List<Map<String, Object>> content = List.of(
                Map.of("type", "text", "text", prompt),
                Map.of("type", "image_url", "image_url", Map.of("url", dataUri)));
        List<Map<String, Object>> messages = new ArrayList<>();
        messages.add(Map.of("role", "user", "content", content));
        String reply = llmClient.chat(messages, null).getContent();
        JsonObject json = JsonParser.parseString(reply.substring(reply.indexOf('{'), reply.lastIndexOf('}') + 1))
                .getAsJsonObject();
        Map<String, String> description = new LinkedHashMap<>();
        for (Map.Entry<String, JsonElement> entry : json.entrySet()) {
            String value = flatten(entry.getValue());
            if (value != null) description.put(entry.getKey(), value);
        }
        return description;
    }
    // ...
}
