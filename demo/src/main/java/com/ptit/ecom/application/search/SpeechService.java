package com.ptit.ecom.application.search;

import com.ptit.ecom.infrastructure.ai.SpeechClient;

/**
 * SpeechService of slide A06: transcribe(audio).
 * The audio goes to the self-hosted Whisper server; null means "please type instead".
 */
public class SpeechService {
    private SpeechClient speechClient;

    public SpeechService(SpeechClient speechClient) {
        this.speechClient = speechClient;
    }

    /** Speech to text in English: "" when no words were heard, null when the Whisper server cannot be reached. */
    public String transcribe(byte[] audioInput) {
        if (audioInput == null || audioInput.length == 0) return "";
        try {
            String text = speechClient.transcribe(audioInput, "en");
            return text == null ? "" : text.replaceAll("[.\\s]+$", "").trim();
        } catch (RuntimeException e) {
            return null;
        }
    }
}
