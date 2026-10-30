public class QueryService {
    // ... (other members omitted)
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
}
