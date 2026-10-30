package com.ptit.ecom.application.service;

import com.ptit.ecom.application.search.SearchService;
import com.ptit.ecom.infrastructure.ai.LlmClient;
import com.ptit.ecom.infrastructure.ai.ToolCall;
import java.util.List;
import java.util.Map;

/**
 * Shopping assistant: Gemma 4 picks a tool, the service runs it (Chapter 3).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class AssistantService {
    private LlmClient llmClient;
    private SearchService searchService;
    private OrderService orderService;

    public AssistantService(LlmClient llmClient, SearchService searchService, OrderService orderService) {
        throw new UnsupportedOperationException("TODO: AssistantService");
    }

    public AssistantReply ask(String customerId, String message) {
        throw new UnsupportedOperationException("TODO: ask");
    }

    private List<Map<String, Object>> tools() {
        throw new UnsupportedOperationException("TODO: tools");
    }

    private String runTool(String customerId, ToolCall call) {
        throw new UnsupportedOperationException("TODO: runTool");
    }
}
