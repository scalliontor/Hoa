package com.ptit.ecom.infrastructure.ai;

/**
 * Calls the self-hosted Whisper server to turn speech into text (slide A06: Speech-to-Text).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class WhisperClient implements SpeechClient {
    private String baseUrl;
    private String model;
    private int timeoutSeconds;

    public WhisperClient(String baseUrl, String model, int timeoutSeconds) {
        throw new UnsupportedOperationException("TODO: WhisperClient");
    }

    @Override
    public String transcribe(byte[] audio, String language) {
        throw new UnsupportedOperationException("TODO: transcribe");
    }

    @Override
    public boolean isAvailable() {
        throw new UnsupportedOperationException("TODO: isAvailable");
    }
}
