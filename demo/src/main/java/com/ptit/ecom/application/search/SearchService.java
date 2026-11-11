package com.ptit.ecom.application.search;

import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.repository.ProductRepository;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * SearchService of slide A06: retrieve candidates, then rank them.
 * Different inputs -> CommonQuery -> retrieval -> ranking -> results (slide A06, eq. 1).
 */
public class SearchService {
    private static final int LIMIT = 12;
    private static final int SHORTLIST = 12;
    private static final List<String> ROOM_WORDS = List.of("sofa", "couch", "wall", "light", "floor", "window",
            "wood", "brick", "cushion", "rug", "chair", "table", "plant", "shelf", "bed", "curtain", "lamp");
    private static final Set<String> STOP_WORDS = Set.of("a", "an", "the", "of", "by", "in", "on", "with", "and",
            "for", "to", "me", "my", "i", "show", "find", "want", "some", "please", "painting", "paintings", "art",
            "artwork", "picture", "pictures", "print", "prints", "under", "below", "less", "than", "dollars", "dollar",
            "usd", "similar", "this", "image", "like", "cheap", "up", "at", "most", "max");
    private ProductRepository repository;
    private QueryService queryService;
    private ImageService imageService;
    private VectorIndex vectorIndex;
    private RankingService rankingService;

    public SearchService(ProductRepository repository, QueryService queryService, ImageService imageService,
                         VectorIndex vectorIndex, RankingService rankingService) {
        this.repository = repository;
        this.queryService = queryService;
        this.imageService = imageService;
        this.vectorIndex = vectorIndex;
        this.rankingService = rankingService;
    }

    /** search_text of slide A06; an empty text lists the whole collection. */
    public List<SearchResult> searchText(String text) {
        CommonQuery query = queryService.textQuery(text);
        int limit = query.getQuery().isEmpty() ? Integer.MAX_VALUE : LIMIT;
        return rankingService.rank(query, retrieve(query), limit);
    }

    /** The Whisper transcript follows the same path as typed text. */
    public List<SearchResult> searchVoice(String transcript) {
        CommonQuery query = queryService.voiceQuery(transcript);
        return rankingService.rank(query, retrieve(query), LIMIT);
    }

    /** "Show me paintings similar to this image": Gemma 4 vision -> vector -> cosine. */
    public List<SearchResult> searchImage(byte[] image) {
        CommonQuery query = queryService.imageQuery(imageService.embed(image));
        copyDescription(query, imageService.describe(image, "artwork"));
        return rankingService.rank(query, retrieve(query), LIMIT);
    }

    /**
     * "Find paintings for my room" (UC14): Gemma 4 reads the room, the vectors shortlist 12 paintings,
     * then Gemma 4 looks at the photo again, picks the 3-5 that fit best and says why in one sentence.
     * Without Gemma the vector ranking stays, with a sentence built from the matching attributes.
     */
    public List<SearchResult> searchRoom(byte[] image) {
        Map<String, String> room = describeRoom(image);
        CommonQuery query = queryService.imageQuery(
                VectorIndex.toVector(room.get("style"), room.get("subject"), room.get("color")));
        query.setType("room");
        copyDescription(query, room);
        query.setArtist(null);
        List<SearchResult> shortlist = new ArrayList<>(rankingService.rank(query, retrieve(query), SHORTLIST));
        fillWithBestSellers(query, shortlist);
        for (SearchResult result : shortlist) result.setReason(roomReason((Painting) result.getProduct(), room));
        List<SearchResult> picks = "gemma".equals(room.get("ai")) ? gemmaPicks(image, room, shortlist) : List.of();
        return picks.isEmpty() ? shortlist.subList(0, Math.min(8, shortlist.size())) : picks;
    }

    public Map<String, String> describeRoom(byte[] image) {
        return imageService.describe(image, "room");
    }

    /** Text and image together, combined by the weights of RankingService (slide A06, eq. 10). */
    public List<SearchResult> searchMultimodal(String text, byte[] image) {
        CommonQuery query = queryService.textQuery(text);
        query.setType("multimodal");
        query.setEmbedding(imageService.embed(image));
        return rankingService.rank(query, retrieve(query), LIMIT);
    }

    /** Candidate retrieval: the hard conditions of UC02 (maximum price; for a typed or spoken request also the
     *  artist it names), then text and image scores for each product. */
    private List<SearchResult> retrieve(CommonQuery query) {
        List<Product> products = repository.allProducts();
        vectorIndex.build(products);
        Map<String, Double> similar = query.getEmbedding() == null ? Map.of()
                : vectorIndex.nearest(query.getEmbedding(), products.size());
        List<SearchResult> candidates = new ArrayList<>();
        for (Product product : products) {
            if (query.getMaxPrice() != null && product.getPrice().compareTo(query.getMaxPrice()) > 0) continue;
            if (namesArtist(query) && !matches(attributePairs(query, product)[3])) continue;
            SearchResult result = new SearchResult(product);
            result.setTextScore(textScore(query, product));
            result.setImageScore(similar.getOrDefault(product.getProductId(), 0.0));
            result.setReason(reason(query, product, result.getImageScore()));
            if (isCandidate(query, result)) candidates.add(result);
        }
        return candidates;
    }

    /** A photo can look like a painter's work without being by that painter, so only words make the artist a filter. */
    private static boolean namesArtist(CommonQuery query) {
        return query.getArtist() != null && ("text".equals(query.getType()) || "voice".equals(query.getType()));
    }

    private boolean isCandidate(CommonQuery query, SearchResult result) {
        switch (query.getType()) {
            case "image":
            case "room":
                return result.getImageScore() > 0;
            case "multimodal":
                return result.getTextScore() > 0 || result.getImageScore() > 0;
            default:
                return query.getQuery().isEmpty() || result.getTextScore() > 0;
        }
    }

    /** Stext: half keyword overlap, half attributes (style, subject, colour, artist) that match. */
    private double textScore(CommonQuery query, Product product) {
        List<String> words = keywords(query.getQuery());
        String text = product.keywords();
        int found = 0;
        for (String word : words) if (text.contains(word)) found++;
        double keywordScore = words.isEmpty() ? 0 : (double) found / words.size();
        int asked = 0, matched = 0;
        for (String[] pair : attributePairs(query, product)) {
            if (pair[0] == null) continue;
            asked++;
            if (matches(pair)) matched++;
        }
        double attributeScore = asked == 0 ? 0 : (double) matched / asked;
        if (words.isEmpty()) return attributeScore;
        return asked == 0 ? keywordScore : (keywordScore + attributeScore) / 2;
    }

    /** Style, subject and colour must be equal; an artist matches by part of the name ("Monet"). */
    private static boolean matches(String[] pair) {
        if (pair[0] == null || pair[1] == null) return false;
        if (pair[2] != null) return pair[1].toLowerCase().contains(pair[0].toLowerCase());
        return pair[1].equalsIgnoreCase(pair[0]);
    }

    /** Triples {asked value, product value, "name" for the artist} for style, subject, colour and artist. */
    private static String[][] attributePairs(CommonQuery query, Product product) {
        Painting painting = product instanceof Painting ? (Painting) product : null;
        return new String[][] {
            {query.getStyle(), painting == null ? null : painting.getStyle(), null},
            {query.getSubject(), painting == null ? null : painting.getSubject(), null},
            {query.getColor(), painting == null ? null : painting.getDominantColor(), null},
            {query.getArtist(), painting == null ? null : painting.getArtist().getName(), "name"},
        };
    }

    /** Why the product is shown, e.g. "Gemma 4 ▪ landscape ▪ blue ▪ under $100"; empty when browsing. */
    private static String reason(CommonQuery query, Product product, double imageScore) {
        if (query.getQuery().isEmpty() && query.getEmbedding() == null) return "";
        List<String> parts = new ArrayList<>();
        parts.add(source(query));
        for (String[] pair : attributePairs(query, product)) {
            if (matches(pair)) parts.add(pair[1]);
        }
        if (query.getMaxPrice() != null) {
            parts.add("under $" + query.getMaxPrice().stripTrailingZeros().toPlainString());
        }
        if (imageScore > 0) parts.add(Math.round(imageScore * 100) + "% visual match");
        return String.join(" ▪ ", parts);
    }

    private static String source(CommonQuery query) {
        if (query.getType().equals("text") || query.getType().equals("voice")) {
            return query.getAiUsed() ? "Gemma 4" : "Keyword rules";
        }
        return query.getAiUsed() ? "Gemma 4 vision" : "Local colour reading";
    }

    /** Copies style, subject, colour and artist that Gemma read from the photo into the query. */
    private static void copyDescription(CommonQuery query, Map<String, String> description) {
        query.setStyle(description.get("style"));
        query.setSubject(description.get("subject"));
        query.setColor(description.get("color"));
        query.setArtist(description.get("artist"));
        query.setAiUsed("gemma".equals(description.get("ai")));
    }

    /** Lower-case words of the request without stop words and numbers. */
    private static List<String> keywords(String text) {
        List<String> words = new ArrayList<>();
        for (String word : Arrays.asList(text.split("[^\\p{L}0-9-]+"))) {
            if (!word.isEmpty() && !STOP_WORDS.contains(word) && !word.matches("\\$?\\d+(\\.\\d+)?")) words.add(word);
        }
        return words;
    }

    // ------------------------------------------------------------ room suggestions (UC14)

    /** Gemma 4 chooses among the shortlist; only ids of the shortlist count, at least three results. */
    private List<SearchResult> gemmaPicks(byte[] image, Map<String, String> room, List<SearchResult> shortlist) {
        StringBuilder purpose = new StringBuilder("pick:");
        for (SearchResult result : shortlist) {
            purpose.append('\n').append(candidateLine((Painting) result.getProduct()));
        }
        List<SearchResult> picks = new ArrayList<>();
        for (Map.Entry<String, String> answer : imageService.describe(image, purpose.toString()).entrySet()) {
            SearchResult result = find(shortlist, answer.getKey());
            if (result == null || picks.contains(result) || picks.size() == 5) continue;
            if (isConcrete(answer.getValue(), room, (Painting) result.getProduct())) {
                result.setReason(answer.getValue().trim());
            }
            picks.add(result);
        }
        for (SearchResult result : shortlist) {
            if (picks.isEmpty() || picks.size() >= 3) break;
            if (!picks.contains(result)) picks.add(result);
        }
        return picks;
    }

    /** One candidate for Gemma: "P03 | Woman with a Parasol | Claude Monet | Impressionism | landscape | ..." */
    private static String candidateLine(Painting painting) {
        return String.join(" | ", painting.getProductId(), painting.getName(), painting.getArtist().getName(),
                painting.getStyle(), painting.getSubject(), painting.getDominantColor(), painting.getMedium(),
                painting.sizeLabel(), painting.getPrice().stripTrailingZeros().toPlainString());
    }

    /** A reason must be one real sentence naming something of the room and something of the painting. */
    private static boolean isConcrete(String reason, Map<String, String> room, Painting painting) {
        if (reason == null) return false;
        String text = reason.toLowerCase();
        int words = text.trim().split("\\s+").length;
        if (words < 10 || words > 40) return false;
        List<String> roomClues = new ArrayList<>(ROOM_WORDS);
        for (String key : List.of("colors", "tone", "light", "interior", "mood", "room")) {
            for (String part : room.getOrDefault(key, "").toLowerCase().split("[,\\s]+")) {
                if (part.length() > 2) roomClues.add(part);
            }
        }
        String artist = painting.getArtist().getName();
        List<String> paintingClues = List.of(painting.getDominantColor(), painting.getSubject().split(" ")[0],
                painting.getStyle().toLowerCase().substring(0, 6), artist.substring(artist.lastIndexOf(' ') + 1));
        return roomClues.stream().anyMatch(text::contains)
                && paintingClues.stream().anyMatch(clue -> text.contains(clue.toLowerCase()));
    }

    /** The sentence used without Gemma's choice, built from the painting and what is known of the room. */
    private static String roomReason(Painting painting, Map<String, String> room) {
        String work = painting.getDominantColor() + " tones and " + styleWord(painting.getStyle()) + " "
                + subjectWord(painting.getSubject());
        if (!room.containsKey("room")) {
            return "Its " + work + " work with the " + room.getOrDefault("color", "main")
                    + " colour read from your photo, and keep the wall calm and simple.";
        }
        String mood = room.getOrDefault("mood", room.getOrDefault("tone", "calm")).toLowerCase().split(",")[0].trim();
        String interior = room.getOrDefault("interior", "simple").toLowerCase();
        String light = room.containsKey("light") ? room.get("light").toLowerCase() + " " : "";
        return "Its " + work + " suit the " + mood + " mood and " + interior + " style of your " + light
                + room.get("room").toLowerCase() + ".";
    }

    private static String styleWord(String style) {
        switch (style) {
            case "Impressionism": return "impressionist";
            case "Post-Impressionism": return "post-impressionist";
            case "Romanticism": return "romantic";
            case "Expressionism": return "expressionist";
            case "Realism": return "realist";
            case "Naive art": return "naive";
            default: return style.toLowerCase();
        }
    }

    private static String subjectWord(String subject) {
        switch (subject) {
            case "flowers": return "flower piece";
            case "cityscape": return "city view";
            case "everyday life": return "everyday scene";
            case "abstract": return "composition";
            default: return subject;
        }
    }

    /** With fewer than three vector matches (Gemma offline, unusual colours), best-selling paintings fill up. */
    private void fillWithBestSellers(CommonQuery query, List<SearchResult> shortlist) {
        if (shortlist.size() >= 3) return;
        List<SearchResult> extra = new ArrayList<>();
        for (Product product : repository.allProducts()) {
            if (product instanceof Painting && find(shortlist, product.getProductId()) == null) {
                extra.add(new SearchResult(product));
            }
        }
        shortlist.addAll(rankingService.rank(query, extra, 8 - shortlist.size()));
    }

    private static SearchResult find(List<SearchResult> results, String productId) {
        for (SearchResult result : results) {
            if (result.getProduct().getProductId().equals(productId)) return result;
        }
        return null;
    }
}
