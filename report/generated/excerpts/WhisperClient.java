public class WhisperClient implements SpeechClient {
    // ... (other members omitted)
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
}
