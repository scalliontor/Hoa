package com.ptit.ecom.infrastructure.ai;

import java.util.List;
import java.util.Map;

/**
 * Interface to the AI model, so Gemma can be replaced without touching services (NFR04).
 * Generated from the 4.4 design model (tools/model.py).
 */
public interface LlmClient {
    LlmReply chat(List<Map<String, Object>> messages, List<Map<String, Object>> tools);

    boolean isAvailable();
}
