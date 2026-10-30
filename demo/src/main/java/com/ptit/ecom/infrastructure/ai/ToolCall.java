package com.ptit.ecom.infrastructure.ai;

/**
 * One tool call chosen by Gemma 4 (tool calling).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class ToolCall {
    private String id;
    private String name;
    private String arguments;

    public ToolCall(String id, String name, String arguments) {
        this.id = id;
        this.name = name;
        this.arguments = arguments;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getArguments() {
        return arguments;
    }
}
