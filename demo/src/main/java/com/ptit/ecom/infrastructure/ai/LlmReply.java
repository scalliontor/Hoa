package com.ptit.ecom.infrastructure.ai;

import java.util.List;

/**
 * Reply of the language model: text content or a list of tool calls.
 * Generated from the 4.4 design model (tools/model.py).
 */
public class LlmReply {
    private String content;
    private List<ToolCall> toolCalls;

    public LlmReply(String content, List<ToolCall> toolCalls) {
        this.content = content;
        this.toolCalls = toolCalls;
    }

    public boolean hasToolCalls() {
        return toolCalls != null && !toolCalls.isEmpty();
    }

    public String getContent() {
        return content;
    }

    public List<ToolCall> getToolCalls() {
        return toolCalls;
    }
}
