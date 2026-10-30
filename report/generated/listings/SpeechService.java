public class SpeechService {
    // ... (other members omitted)
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
