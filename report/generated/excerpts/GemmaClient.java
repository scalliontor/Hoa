public class GemmaClient implements LlmClient {
    // ... (other members omitted)
    /** POST /chat/completions; any network or HTTP error becomes an exception so callers can fall back. */
    @Override
    public LlmReply chat(List<Map<String, Object>> messages, List<Map<String, Object>> tools) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", model);
        body.put("messages", messages);
        body.put("temperature", 0.2);
        body.put("max_tokens", 700);
        if (tools != null && !tools.isEmpty()) {
            body.put("tools", tools);
            body.put("tool_choice", "auto");
        }
        HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "chat/completions"))
                .timeout(Duration.ofSeconds(timeoutSeconds))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(GSON.toJson(body)))
                .build();
        return toReply(send(request));
    }
}
