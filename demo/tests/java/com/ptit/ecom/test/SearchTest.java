package com.ptit.ecom.test;

import static com.ptit.ecom.test.Fixtures.freshDatabase;
import static com.ptit.ecom.test.Fixtures.painting;
import static com.ptit.ecom.test.Fixtures.searchService;
import static com.ptit.ecom.test.TestRunner.check;
import static com.ptit.ecom.test.TestRunner.same;
import static com.ptit.ecom.test.TestRunner.test;

import com.ptit.ecom.application.search.CommonQuery;
import com.ptit.ecom.application.search.ImageService;
import com.ptit.ecom.application.search.QueryService;
import com.ptit.ecom.application.search.RankingService;
import com.ptit.ecom.application.search.SearchResult;
import com.ptit.ecom.application.search.SpeechService;
import com.ptit.ecom.domain.product.Painting;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import com.ptit.ecom.test.Fixtures.FakeLlmClient;
import com.ptit.ecom.test.Fixtures.FakeSpeechClient;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import javax.imageio.ImageIO;

/** Query understanding, vectors, cosine similarity and ranking of slide A06, with a fake Gemma 4. */
final class SearchTest {
    private SearchTest() {
    }

    static void run() {
        test("cosineSimilarity follows the slide formula", () -> {
            same(1.0, VectorIndex.cosineSimilarity(new double[] {1, 0}, new double[] {1, 0}), "same direction");
            same(0.0, VectorIndex.cosineSimilarity(new double[] {1, 0}, new double[] {0, 1}), "orthogonal");
            check(Math.abs(VectorIndex.cosineSimilarity(new double[] {1, 1}, new double[] {1, 0}) - Math.sqrt(0.5)) < 1e-9,
                    "45 degrees");
            same(0.0, VectorIndex.cosineSimilarity(new double[] {0, 0}, new double[] {1, 0}), "zero vector");
        });
        test("toVector is one-hot: 10 styles + 8 subjects + 10 colours = 28 dimensions", () -> {
            double[] vector = VectorIndex.toVector("Ukiyo-e", "seascape", "blue");
            same(28, vector.length, "dimensions");
            same(3.0, sum(vector), "three ones");
            same(0.0, sum(VectorIndex.toVector("Cubism", "battle", "turquoise")), "unknown values");
        });
        test("RankingService: S = 0.45 Stext + 0.45 Simage + 0.10 Sbusiness, best first, limited", () -> {
            RankingService ranking = new RankingService(0.45, 0.45, 0.10);
            SearchResult best = result(painting("P01", "79", 10), 1.0, 0.5);
            SearchResult soldOut = result(painting("P02", "69", 0), 1.0, 0.5);
            SearchResult weak = result(painting("P03", "89", 2), 0.0, 0.5);
            List<SearchResult> ranked = ranking.rank(new CommonQuery("text", "x"), List.of(weak, soldOut, best), 2);
            same(2, ranked.size(), "limit");
            check(Math.abs(best.getScore() - 0.775) < 1e-9, "0.45*1 + 0.45*0.5 + 0.10*1 = 0.775, got " + best.getScore());
            same(0.0, soldOut.getBusinessScore(), "sold-out business score");
            same("P01", ranked.get(0).getProduct().getProductId(), "best first");
            check(Math.abs(weak.getBusinessScore() - 0.4) < 1e-9, "stock 2 of 5 -> 0.4");
        });
        test("Gemma's JSON becomes a CommonQuery (style, artist, max price)", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().answer("{\"style\": \"Impressionism\", \"subject\": null, "
                    + "\"color\": null, \"artist\": \"Claude Monet\", \"max_price\": 100}");
            CommonQuery query = new QueryService(gemma).textQuery("Monet paintings under 100 dollars");
            same("Impressionism", query.getStyle(), "style");
            same("Claude Monet", query.getArtist(), "artist");
            same(0, new BigDecimal("100").compareTo(query.getMaxPrice()), "max price");
            check(query.getAiUsed(), "AI used");
        });
        test("Values outside the catalogue vocabulary are dropped", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().answer("Sure! {\"style\": \"Cubism\", \"color\": \"turquoise\"}");
            CommonQuery query = new QueryService(gemma).textQuery("cubist turquoise art");
            same(null, query.getStyle(), "style");
            same(null, query.getColor(), "colour");
        });
        test("Keyword rules replace Gemma when it is offline (NFR02)", () -> {
            QueryService rules = new QueryService(FakeLlmClient.offline());
            CommonQuery blue = rules.textQuery("blue landscape paintings");
            same("blue", blue.getColor(), "colour");
            same("landscape", blue.getSubject(), "subject");
            check(!blue.getAiUsed(), "rules, not AI");
            CommonQuery monet = rules.textQuery("Monet paintings under 100 dollars");
            same(0, new BigDecimal("100").compareTo(monet.getMaxPrice()), "max price");
            same(null, rules.textQuery("a hundred flowers").getColor(), "'red' is not read inside 'hundred'");
        });
        test("Offline search still puts Monet first and respects the price limit", () -> {
            List<SearchResult> results = searchService(freshDatabase(), FakeLlmClient.offline())
                    .searchText("Monet paintings under 100 dollars");
            for (SearchResult result : results.subList(0, 3)) {
                same("Claude Monet", ((Painting) result.getProduct()).getArtist().getName(), "artist");
                check(result.getReason().startsWith("Keyword rules"), "reason " + result.getReason());
            }
            for (SearchResult result : results) {
                check(result.getProduct().getPrice().compareTo(new BigDecimal("100")) <= 0, "price filter");
            }
        });
        test("Text search with Gemma: blue landscape paintings", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().answer("{\"subject\": \"landscape\", \"color\": \"blue\"}");
            List<SearchResult> results = searchService(freshDatabase(), gemma).searchText("blue landscape paintings");
            for (SearchResult result : results.subList(0, 3)) {
                Painting painting = (Painting) result.getProduct();
                same("landscape", painting.getSubject(), "subject of " + painting.getName());
                same("blue", painting.getDominantColor(), "colour of " + painting.getName());
                check(result.getReason().startsWith("Gemma 4"), "reason " + result.getReason());
            }
        });
        test("Image search: Gemma's reading of a photo finds the painting (cosine = 1)", () -> {
            FakeLlmClient gemma = FakeLlmClient.online().answer("{\"style\": \"Post-Impressionism\", "
                    + "\"subject\": \"flowers\", \"color\": \"yellow\", \"artist\": \"Vincent van Gogh\"}");
            List<SearchResult> results = searchService(freshDatabase(), gemma).searchImage(png(Color.YELLOW));
            same("P06", results.get(0).getProduct().getProductId(), "Sunflowers first");
            check(Math.abs(results.get(0).getImageScore() - 1.0) < 1e-9, "image score " + results.get(0).getImageScore());
            same(1, gemma.conversations.size(), "one Gemma call for describe + embed");
        });
        test("Room search (UC14): Gemma picks 3-5 shortlisted paintings, each with one concrete sentence", () -> {
            FakeLlmClient gemma = FakeLlmClient.online()
                    .answer("{\"room\": \"living room\", \"colors\": [\"grey\", \"white\"], \"tone\": \"cool\", "
                            + "\"interior\": \"modern minimalist\", \"mood\": \"calm\", \"light\": \"bright\", "
                            + "\"style\": \"Impressionism\", \"subject\": \"landscape\", \"color\": \"blue\"}")
                    .answer("{\"P03\": \"Its soft blues echo your grey sofa and keep the calm mood of this bright "
                            + "modern living room.\", \"P99\": \"A painting that is not on the shortlist at all, so it "
                            + "must be ignored.\", \"P05\": \"Nice.\"}");
            List<SearchResult> results = searchService(freshDatabase(), gemma).searchRoom(png(Color.GRAY));
            check(results.size() >= 3 && results.size() <= 5, "3 to 5 picks, got " + ids(results));
            same("P03", results.get(0).getProduct().getProductId(), "Gemma's first choice");
            check(results.get(0).getReason().startsWith("Its soft blues echo your grey sofa"), results.get(0).getReason());
            check(!ids(results).contains("P99"), "ids outside the shortlist are ignored");
            same("P05", results.get(1).getProduct().getProductId(), "second choice kept");
            check(results.get(1).getReason().contains("calm mood and modern minimalist style"),
                    "a too short reason is replaced by the attribute sentence: " + results.get(1).getReason());
            check(gemma.conversations.get(1).toString().contains("P03 | Woman with a Parasol | Claude Monet"),
                    "the shortlist is sent to Gemma with the photo");
        });
        test("Room search without Gemma: vector ranking, one full sentence per painting (NFR02)", () -> {
            List<SearchResult> results = searchService(freshDatabase(), FakeLlmClient.offline())
                    .searchRoom(png(new Color(40, 90, 170)));
            check(results.size() >= 3, "suggestions " + ids(results));
            for (SearchResult result : results) {
                String reason = result.getReason();
                check(reason.startsWith("Its ") && reason.endsWith(".") && reason.split(" ").length >= 12, reason);
            }
        });
        test("Without Gemma the photo's average colour is read on the server", () -> {
            Map<String, String> room = new ImageService(FakeLlmClient.offline()).describe(png(new Color(40, 90, 170)), "room");
            same("local", room.get("ai"), "source");
            same("blue", room.get("color"), "colour");
        });
        test("SpeechService asks Whisper in English: transcript, \"\" when nothing is heard, null when it is down", () -> {
            FakeSpeechClient whisper = new FakeSpeechClient("Blue landscape paintings.");
            same("Blue landscape paintings", new SpeechService(whisper).transcribe(new byte[] {1, 2, 3}), "transcript");
            same("en", whisper.lastLanguage, "language");
            same("", new SpeechService(new FakeSpeechClient(" ")).transcribe(new byte[] {1}), "silence");
            same(null, new SpeechService(new FakeSpeechClient(null)).transcribe(new byte[] {1}), "server down");
        });
    }

    private static SearchResult result(Painting painting, double text, double image) {
        SearchResult result = new SearchResult(painting);
        result.setTextScore(text);
        result.setImageScore(image);
        return result;
    }

    private static double sum(double[] vector) {
        double total = 0;
        for (double value : vector) total += value;
        return total;
    }

    static byte[] png(Color color) throws Exception {
        BufferedImage image = new BufferedImage(64, 48, BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = image.createGraphics();
        graphics.setColor(color);
        graphics.fillRect(0, 0, 64, 48);
        graphics.dispose();
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ImageIO.write(image, "png", out);
        return out.toByteArray();
    }

    static List<String> ids(List<SearchResult> results) {
        List<String> ids = new ArrayList<>();
        for (SearchResult result : results) ids.add(result.getProduct().getProductId());
        return ids;
    }
}
