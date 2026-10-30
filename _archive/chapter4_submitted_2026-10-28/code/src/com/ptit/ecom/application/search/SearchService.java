package com.ptit.ecom.application.search;

import com.ptit.ecom.domain.product.Product;
import com.ptit.ecom.infrastructure.dao.ProductDAO;
import com.ptit.ecom.infrastructure.search.VectorIndex;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class SearchService {
    private QueryService queryService;
    private RankingService rankingService;
    private ProductDAO productDAO;
    private VectorIndex vectorIndex;

    public SearchService(QueryService queryService, RankingService rankingService, ProductDAO productDAO, VectorIndex vectorIndex) {
        this.queryService = queryService;
        this.rankingService = rankingService;
        this.productDAO = productDAO;
        this.vectorIndex = vectorIndex;
    }

    public List<SearchResult> searchText(String text) {
        CommonQuery query = queryService.buildTextQuery(text);
        List<SearchResult> candidates = new ArrayList<>();
        for (Product product : productDAO.searchByKeyword(query.getText(), 100)) {
            candidates.add(new SearchResult(product, textScore(query.getText(), product.getName())));
        }
        return rankingService.rank(query, candidates, 5);
    }

    public List<SearchResult> searchVoice(String transcript) {
        // A voice transcript follows the same retrieval path as typed text.
        return searchText(queryService.buildVoiceQuery(transcript).getText());
    }

    public List<SearchResult> searchImage(byte[] image) {
        CommonQuery query = queryService.buildImageQuery(vectorIndex.embed(image));
        List<SearchResult> candidates = new ArrayList<>();
        for (Map.Entry<String, Double> hit : vectorIndex.nearest(query.getImageVector(), 20).entrySet()) {
            Product product = productDAO.findById(hit.getKey());
            if (product != null) candidates.add(new SearchResult(product, hit.getValue()));
        }
        return rankingService.rank(query, candidates, 5);
    }

    private static double textScore(String query, String name) {
        String lower = name.toLowerCase();
        String[] words = query.split(" ");
        int hits = 0;
        for (String word : words) {
            if (lower.contains(word)) hits++;
        }
        return (double) hits / words.length;
    }
}
