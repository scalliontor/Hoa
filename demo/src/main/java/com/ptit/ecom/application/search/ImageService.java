package com.ptit.ecom.application.search;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.ptit.ecom.infrastructure.ai.LlmClient;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.imageio.ImageIO;

/**
 * ImageService of slide A06: image to feature vector f(I).
 * Gemma 4 vision reads a painting (style, subject, colour) or a room (palette, mood, wall); the photo stays in memory.
 */
public class ImageService {
    private static final String VOCABULARY = "style is one of: Impressionism, Post-Impressionism, Ukiyo-e, "
            + "Art Nouveau, Baroque, Romanticism, Expressionism, Abstract, Realism, Naive art. subject is one of: "
            + "landscape, seascape, flowers, portrait, still life, cityscape, everyday life, abstract. "
            + "color is one of: blue, green, yellow, red, orange, brown, white, black, purple, pink.";
    private static final String ARTWORK_PROMPT = "Look at this picture of a painting or an object. Reply with one "
            + "JSON object only, with the keys style, subject, color, artist, title. " + VOCABULARY
            + " color is the dominant colour. artist and title only if you recognise a known painting, else null.";
    private static final String ROOM_PROMPT = "This is a photo of a room. Read it like an art curator choosing a "
            + "painting for the wall. Reply with one JSON object only, with the keys: room (kind of room, 1-3 words), "
            + "palette (array of 4 hex colours of the room), colors (array of 1-3 colour names of the room), "
            + "tone (warm | cool | neutral), interior (interior style, 1-3 words), mood (1-3 words), "
            + "light (bright | soft | dim), style (the ONE painting style that fits best), subject (the ONE painting "
            + "subject that fits best), color (the ONE dominant painting colour that fits best), reading (one short "
            + "sentence about the room and the painting to hang), wall_box (array [x, y, w, h] in 0..1 of the largest "
            + "empty wall area, or null). " + VOCABULARY;
    private static final String PICK_PROMPT = "This is a photo of a customer's room. You are the curator of an online "
            + "shop of painting prints. Choose the 3 to 5 paintings from the candidates below that fit this room best. "
            + "Reply with one JSON object only. Its keys are the productId of the chosen paintings, best first. Each "
            + "value is ONE English sentence of 15 to 25 words that explains why the painting fits: name concrete "
            + "things you see in the photo (wall or sofa colours, light, interior style, mood) and the painting's own "
            + "colours, subject or style. Example: {\"P03\": \"Its soft blues and greens echo your grey sofa and keep "
            + "the calm, airy mood of this bright living room.\"}. Candidates (productId | title | artist | style | "
            + "subject | dominant colour | medium | size | price in USD):";
    private static final String[] COLOR_NAMES = {"blue", "green", "yellow", "red", "orange", "brown", "white",
            "black", "purple", "pink"};
    private static final int[][] COLOR_RGB = {{52, 101, 164}, {80, 140, 80}, {220, 190, 60}, {190, 50, 50},
            {225, 130, 50}, {130, 90, 60}, {235, 235, 230}, {30, 30, 30}, {120, 80, 150}, {225, 150, 170}};
    private LlmClient llmClient;
    private Map<String, Map<String, String>> described = new HashMap<>();

    public ImageService(LlmClient llmClient) {
        this.llmClient = llmClient;
    }

    /** f(I): the photo becomes the same one-hot vector as the catalogue paintings. */
    public double[] embed(byte[] image) {
        Map<String, String> description = describe(image, "artwork");
        return VectorIndex.toVector(description.get("style"), description.get("subject"), description.get("color"));
    }

    /**
     * purpose is "artwork", "room", or "pick:" followed by candidate lines (Gemma then answers productId -> reason).
     * Gemma's answer is remembered, so the same photo and question call Gemma only once.
     */
    public Map<String, String> describe(byte[] image, String purpose) {
        String key = purpose + ":" + Arrays.hashCode(image);
        if (described.containsKey(key)) return described.get(key);
        try {
            Map<String, String> description = askGemma(image, prompt(purpose));
            description.put("ai", "gemma");
            if (described.size() > 50) described.clear();
            described.put(key, description);
            return description;
        } catch (RuntimeException e) {
            return readColorLocally(image);
        }
    }

    private static String prompt(String purpose) {
        if (purpose.startsWith("pick:")) return PICK_PROMPT + purpose.substring("pick:".length());
        return "room".equals(purpose) ? ROOM_PROMPT : ARTWORK_PROMPT;
    }

    private Map<String, String> askGemma(byte[] image, String prompt) {
        String dataUri = "data:" + mimeType(image) + ";base64," + Base64.getEncoder().encodeToString(image);
        List<Map<String, Object>> content = List.of(
                Map.of("type", "text", "text", prompt),
                Map.of("type", "image_url", "image_url", Map.of("url", dataUri)));
        List<Map<String, Object>> messages = new ArrayList<>();
        messages.add(Map.of("role", "user", "content", content));
        String reply = llmClient.chat(messages, null).getContent();
        JsonObject json = JsonParser.parseString(reply.substring(reply.indexOf('{'), reply.lastIndexOf('}') + 1))
                .getAsJsonObject();
        Map<String, String> description = new LinkedHashMap<>();
        for (Map.Entry<String, JsonElement> entry : json.entrySet()) {
            String value = flatten(entry.getValue());
            if (value != null) description.put(entry.getKey(), value);
        }
        return description;
    }

    /** Arrays become "a,b,c" and objects their "reason", so the result fits Map<String, String>. */
    private static String flatten(JsonElement value) {
        if (value == null || value.isJsonNull()) return null;
        if (value.isJsonObject()) return flatten(value.getAsJsonObject().get("reason"));
        if (!value.isJsonArray()) return value.getAsString();
        List<String> parts = new ArrayList<>();
        for (JsonElement element : value.getAsJsonArray()) parts.add(flatten(element));
        return String.join(",", parts);
    }

    /** Offline fallback (NFR02): the average colour of the photo, named with the catalogue colours. */
    private static Map<String, String> readColorLocally(byte[] image) {
        Map<String, String> description = new LinkedHashMap<>();
        description.put("ai", "local");
        try {
            BufferedImage picture = ImageIO.read(new ByteArrayInputStream(image));
            if (picture == null) return description;
            long red = 0, green = 0, blue = 0, count = 0;
            for (int y = 0; y < picture.getHeight(); y += 8) {
                for (int x = 0; x < picture.getWidth(); x += 8) {
                    int rgb = picture.getRGB(x, y);
                    red += (rgb >> 16) & 255;
                    green += (rgb >> 8) & 255;
                    blue += rgb & 255;
                    count++;
                }
            }
            int r = (int) (red / count), g = (int) (green / count), b = (int) (blue / count);
            description.put("color", nearestColor(r, g, b));
            description.put("colors", nearestColor(r, g, b));
            description.put("palette", String.format("#%02x%02x%02x", r, g, b));
            description.put("reading", "Gemma 4 is not reachable, so only the main colour was read on this computer.");
        } catch (IOException e) {
            description.put("reading", "The photo could not be read.");
        }
        return description;
    }

    private static String nearestColor(int r, int g, int b) {
        int best = 0;
        double bestDistance = Double.MAX_VALUE;
        for (int i = 0; i < COLOR_RGB.length; i++) {
            double distance = Math.pow(r - COLOR_RGB[i][0], 2) + Math.pow(g - COLOR_RGB[i][1], 2)
                    + Math.pow(b - COLOR_RGB[i][2], 2);
            if (distance < bestDistance) {
                bestDistance = distance;
                best = i;
            }
        }
        return COLOR_NAMES[best];
    }

    private static String mimeType(byte[] image) {
        if (image.length > 3 && image[0] == (byte) 0x89 && image[1] == 'P') return "image/png";
        if (image.length > 11 && image[8] == 'W' && image[9] == 'E' && image[10] == 'B') return "image/webp";
        return "image/jpeg";
    }
}
