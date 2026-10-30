package com.ptit.ecom.infrastructure.ai;

/**
 * Interface to the speech-recognition service (slide A06: Speech-to-Text).
 * Generated from the 4.4 design model (tools/model.py).
 */
public interface SpeechClient {
    String transcribe(byte[] audio, String language);

    boolean isAvailable();
}
