package com.ptit.ecom.application.search;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class QueryService {
    public CommonQuery buildTextQuery(String text) {
        String normalized = text == null ? "" : text.toLowerCase().trim().replaceAll("\\s+", " ");
        if (normalized.isEmpty()) throw new IllegalArgumentException("Query text is required");
        return new CommonQuery("text", normalized, null, null);
    }

    public CommonQuery buildVoiceQuery(String transcript) {
        CommonQuery query = buildTextQuery(transcript);
        return new CommonQuery("voice", query.getText(), null, null);
    }

    public CommonQuery buildImageQuery(float[] imageVector) {
        return new CommonQuery("image", "", imageVector, null);
    }
}
