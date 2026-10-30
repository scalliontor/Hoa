package com.ptit.ecom.application.search;

import com.ptit.ecom.infrastructure.ai.LlmClient;
import java.util.Map;

/**
 * ImageService of slide A06: image to feature vector f(I).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class ImageService {
    private LlmClient llmClient;

    public ImageService(LlmClient llmClient) {
        throw new UnsupportedOperationException("TODO: ImageService");
    }

    public double[] embed(byte[] image) {
        throw new UnsupportedOperationException("TODO: embed");
    }

    public Map<String, String> describe(byte[] image, String purpose) {
        throw new UnsupportedOperationException("TODO: describe");
    }
}
