package com.ptit.ecom.infrastructure.ai;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Calls Gemma 4 through the OpenAI-compatible API (Chapter 3: AI in e-commerce).
 * Server, key and model are those of HUONG_DAN_GOI_GEMMA4.md; the base URL ends with "/".
 */
public class GemmaClient implements LlmClient {
    private static final Gson GSON = new Gson();
    private static final HttpClient HTTP = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(3)).build();
    private String baseUrl;
    private String apiKey;
    private String model;
    private int timeoutSeconds;

    public GemmaClient(String baseUrl, String apiKey, String model, int timeoutSeconds) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.model = model;
        this.timeoutSeconds = timeoutSeconds;
    }

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

    @Override
    public boolean isAvailable() {
        HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "models"))
                .timeout(Duration.ofSeconds(5))
                .header("Authorization", "Bearer " + apiKey)
                .GET().build();
        try {
            send(request);
            return true;
        } catch (RuntimeException e) {
            return false;
        }
    }

    private String send(HttpRequest request) {
        try {
            HttpResponse<String> response = HTTP.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                throw new IllegalStateException("Gemma returned HTTP " + response.statusCode());
            }
            return response.body();
        } catch (IOException e) {
            throw new IllegalStateException("Gemma is unreachable: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Gemma call interrupted", e);
        }
    }

    /** Reads choices[0].message: its text content and its tool_calls, if any. */
    private LlmReply toReply(String json) {
        JsonObject message = JsonParser.parseString(json).getAsJsonObject()
                .getAsJsonArray("choices").get(0).getAsJsonObject()
                .getAsJsonObject("message");
        JsonElement content = message.get("content");
        List<ToolCall> calls = new ArrayList<>();
        JsonElement toolCalls = message.get("tool_calls");
        if (toolCalls != null && toolCalls.isJsonArray()) {
            for (JsonElement element : toolCalls.getAsJsonArray()) {
                JsonObject call = element.getAsJsonObject();
                JsonObject function = call.getAsJsonObject("function");
                calls.add(new ToolCall(call.get("id").getAsString(), function.get("name").getAsString(),
                        function.get("arguments").getAsString()));
            }
        }
        return new LlmReply(content == null || content.isJsonNull() ? null : content.getAsString(), calls);
    }
}
