package com.ptit.ecom.infrastructure.ai;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

/**
 * Calls the self-hosted Whisper server to turn speech into text (slide A06: Speech-to-Text).
 * API of demo/voice-server: POST {baseUrl}/transcribe?language=en with the raw audio bytes as body.
 */
public class WhisperClient implements SpeechClient {
    private static final HttpClient HTTP = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
    private String baseUrl;
    private String model;
    private int timeoutSeconds;

    public WhisperClient(String baseUrl, String model, int timeoutSeconds) {
        this.baseUrl = baseUrl;
        this.model = model;
        this.timeoutSeconds = timeoutSeconds;
    }

    /** Returns the transcript; the audio never leaves the machine. */
    @Override
    public String transcribe(byte[] audio, String language) {
        String url = baseUrl + "/transcribe?language=" + URLEncoder.encode(language, StandardCharsets.UTF_8)
                + "&model=" + URLEncoder.encode(model, StandardCharsets.UTF_8);
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(timeoutSeconds))
                .header("Content-Type", "application/octet-stream")
                .POST(HttpRequest.BodyPublishers.ofByteArray(audio))
                .build();
        JsonObject result = JsonParser.parseString(send(request)).getAsJsonObject();
        return result.get("text").getAsString().trim();
    }

    @Override
    public boolean isAvailable() {
        HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "/health"))
                .timeout(Duration.ofSeconds(2)).GET().build();
        try {
            send(request);
            return true;
        } catch (RuntimeException e) {
            return false;
        }
    }

    private String send(HttpRequest request) {
        try {
            HttpResponse<String> response = HTTP.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                throw new IllegalStateException("Whisper returned HTTP " + response.statusCode() + ": " + response.body());
            }
            return response.body();
        } catch (IOException e) {
            throw new IllegalStateException("Whisper server is not running: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Whisper call interrupted", e);
        }
    }
}
