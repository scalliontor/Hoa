package com.ptit.ecom.infrastructure.search;

import java.util.Map;

/**
 * Generated from the Chapter 4.4 design model (tools/model.py).
 * Adapter to the image-feature engine (Apple Vision in the A6 prototype).
 */
public class VectorIndex {
    private String modelVersion;

    public float[] embed(byte[] image) {
        throw new UnsupportedOperationException("TODO: embed");
    }

    public Map<String, Double> nearest(float[] vector, int k) {
        throw new UnsupportedOperationException("TODO: nearest");
    }
}
