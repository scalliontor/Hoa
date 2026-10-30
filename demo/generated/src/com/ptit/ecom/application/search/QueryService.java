package com.ptit.ecom.application.search;

import com.ptit.ecom.infrastructure.ai.LlmClient;

/**
 * QueryService of slide A06: text_query, voice_query, image_query.
 * Generated from the 4.4 design model (tools/model.py).
 */
public class QueryService {
    private LlmClient llmClient;

    public QueryService(LlmClient llmClient) {
        throw new UnsupportedOperationException("TODO: QueryService");
    }

    public CommonQuery textQuery(String text) {
        throw new UnsupportedOperationException("TODO: textQuery");
    }

    public CommonQuery voiceQuery(String text) {
        throw new UnsupportedOperationException("TODO: voiceQuery");
    }

    public CommonQuery imageQuery(double[] embedding) {
        throw new UnsupportedOperationException("TODO: imageQuery");
    }

    private void understand(CommonQuery query) {
        throw new UnsupportedOperationException("TODO: understand");
    }

    private void parseRules(CommonQuery query) {
        throw new UnsupportedOperationException("TODO: parseRules");
    }
}
