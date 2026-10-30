package com.ptit.ecom.application.service;

import java.util.List;

/**
 * Answer of the shopping assistant.
 * Generated from the 4.4 design model (tools/model.py).
 */
public class AssistantReply {
    private String answer;
    private List<String> toolsUsed;
    private boolean aiUsed;

    public AssistantReply(String answer, List<String> toolsUsed, boolean aiUsed) {
        this.answer = answer;
        this.toolsUsed = toolsUsed;
        this.aiUsed = aiUsed;
    }

    public String getAnswer() {
        return answer;
    }

    public List<String> getToolsUsed() {
        return toolsUsed;
    }

    public boolean getAiUsed() {
        return aiUsed;
    }
}
