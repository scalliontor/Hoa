package com.ptit.ecom.application.search;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.ptit.ecom.infrastructure.ai.LlmClient;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * QueryService of slide A06: text_query, voice_query, image_query.
 * Every input becomes one CommonQuery; Gemma 4 reads the filters, keyword rules are the fallback (NFR02).
 */
public class QueryService {
    private static final String PROMPT = "You turn a shopper's request for an online painting shop into JSON. "
            + "Reply with one JSON object only, with the keys style, subject, color, artist, max_price. "
            + "style is one of: Impressionism, Post-Impressionism, Ukiyo-e, Art Nouveau, Baroque, Romanticism, "
            + "Expressionism, Abstract, Realism, Naive art. subject is one of: landscape, seascape, flowers, portrait, "
            + "still life, cityscape, everyday life, abstract. color is one of: blue, green, yellow, red, orange, "
            + "brown, white, black, purple, pink. artist is the painter's name if one is mentioned. max_price is a "
            + "number in US dollars if the request gives an upper price. Use null for anything the request does "
            + "not ask for.";
    private static final Pattern PRICE = Pattern.compile(
            "(under|below|less than|cheaper than|up to|at most|max|<)\\s*\\$?\\s*(\\d+(?:\\.\\d+)?)");
    private static final String[][] SYNONYMS = {
            // word in the request -> {field, canonical value}
            {"post-impressionis", "style", "Post-Impressionism"}, {"impressionis", "style", "Impressionism"},
            {"ukiyo", "style", "Ukiyo-e"}, {"japanese", "style", "Ukiyo-e"}, {"art nouveau", "style", "Art Nouveau"},
            {"baroque", "style", "Baroque"}, {"romantic", "style", "Romanticism"},
            {"expressionis", "style", "Expressionism"}, {"realis", "style", "Realism"}, {"naive", "style", "Naive art"},
            {"landscape", "subject", "landscape"}, {"seascape", "subject", "seascape"}, {"sea", "subject", "seascape"},
            {"ocean", "subject", "seascape"}, {"wave", "subject", "seascape"}, {"flower", "subject", "flowers"},
            {"floral", "subject", "flowers"}, {"portrait", "subject", "portrait"}, {"still life", "subject", "still life"},
            {"city", "subject", "cityscape"}, {"street", "subject", "cityscape"}, {"everyday", "subject", "everyday life"},
            {"abstract", "subject", "abstract"}, {"abstract", "style", "Abstract"},
            {"blue", "color", "blue"}, {"green", "color", "green"}, {"yellow", "color", "yellow"},
            {"gold", "color", "yellow"}, {"red", "color", "red"}, {"orange", "color", "orange"},
            {"brown", "color", "brown"}, {"white", "color", "white"}, {"black", "color", "black"},
            {"purple", "color", "purple"}, {"violet", "color", "purple"}, {"pink", "color", "pink"},
    };
    private LlmClient llmClient;

    public QueryService(LlmClient llmClient) {
        this.llmClient = llmClient;
    }

    /** text_query of slide A06. */
    public CommonQuery textQuery(String text) {
        CommonQuery query = new CommonQuery("text", normalize(text));
        if (!query.getQuery().isEmpty()) understand(query);
        return query;
    }

    /** voice_query of slide A06: the transcript follows the text path. */
    public CommonQuery voiceQuery(String text) {
        CommonQuery query = textQuery(text);
        query.setType("voice");
        return query;
    }

    /** image_query of slide A06: the query is the image embedding. */
    public CommonQuery imageQuery(double[] embedding) {
        CommonQuery query = new CommonQuery("image", "");
        query.setEmbedding(embedding);
        return query;
    }

    /** Asks Gemma 4 for the filters; on any error the keyword rules are used instead. */
    private void understand(CommonQuery query) {
        try {
            String content = llmClient.chat(List.of(
                    Map.of("role", "system", "content", PROMPT),
                    Map.of("role", "user", "content", query.getQuery())), null).getContent();
            JsonObject json = JsonParser.parseString(content.substring(content.indexOf('{'),
                    content.lastIndexOf('}') + 1)).getAsJsonObject();
            query.setStyle(known(text(json, "style"), "style"));
            query.setSubject(known(text(json, "subject"), "subject"));
            query.setColor(known(text(json, "color"), "color"));
            query.setArtist(text(json, "artist"));
            String price = text(json, "max_price");
            query.setMaxPrice(price == null ? null : new BigDecimal(price.replaceAll("[^0-9.]", "")));
            query.setAiUsed(true);
        } catch (RuntimeException e) {
            parseRules(query);
        }
    }

    /** Fallback without AI: an upper price and the first style, subject and colour words found. */
    private void parseRules(CommonQuery query) {
        String text = query.getQuery();
        Matcher price = PRICE.matcher(text);
        if (price.find()) query.setMaxPrice(new BigDecimal(price.group(2)));
        for (String[] rule : SYNONYMS) {
            if (!startsWord(text, rule[0])) continue;
            if (rule[1].equals("style") && query.getStyle() == null) query.setStyle(rule[2]);
            if (rule[1].equals("subject") && query.getSubject() == null) query.setSubject(rule[2]);
            if (rule[1].equals("color") && query.getColor() == null) query.setColor(rule[2]);
        }
        query.setAiUsed(false);
    }

    /** True if a word of the text starts with the stem, so "red" is not found inside "hundred". */
    private static boolean startsWord(String text, String stem) {
        return Pattern.compile("(^|[^a-z])" + Pattern.quote(stem)).matcher(text).find();
    }

    private static String normalize(String text) {
        return text == null ? "" : text.toLowerCase().trim().replaceAll("\\s+", " ");
    }

    private static String text(JsonObject json, String key) {
        JsonElement value = json.get(key);
        if (value == null || value.isJsonNull()) return null;
        String text = value.getAsString().trim();
        return text.isEmpty() || text.equalsIgnoreCase("null") ? null : text;
    }

    /** Keeps a style / subject / colour only if it belongs to the vocabulary of VectorIndex. */
    private static String known(String value, String field) {
        if (value == null) return null;
        double[] vector = field.equals("style") ? VectorIndex.toVector(value, null, null)
                : field.equals("subject") ? VectorIndex.toVector(null, value, null)
                : VectorIndex.toVector(null, null, value);
        for (double x : vector) if (x > 0) return value;
        return null;
    }
}
