package com.ptit.ecom.infrastructure.ai;

import java.util.List;
import java.util.Map;

/**
 * Calls Gemma 4 through the OpenAI-compatible API (Chapter 3: AI in e-commerce).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class GemmaClient implements LlmClient {
    private String baseUrl;
    private String apiKey;
    private String model;
    private int timeoutSeconds;

    public GemmaClient(String baseUrl, String apiKey, String model, int timeoutSeconds) {
        throw new UnsupportedOperationException("TODO: GemmaClient");
    }

    @Override
    public LlmReply chat(List<Map<String, Object>> messages, List<Map<String, Object>> tools) {
        throw new UnsupportedOperationException("TODO: chat");
    }

    @Override
    public boolean isAvailable() {
        throw new UnsupportedOperationException("TODO: isAvailable");
    }
}
