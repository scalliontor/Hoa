package com.ptit.ecom.application.search;

import java.util.ArrayList;
import java.util.List;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class RankingService {
    public List<SearchResult> rank(CommonQuery query, List<SearchResult> candidates, int limit) {
        List<SearchResult> ranked = new ArrayList<>();
        for (SearchResult candidate : candidates) {
            if (candidate.getProduct().isAvailable(1)) ranked.add(candidate);
        }
        ranked.sort((a, b) -> Double.compare(b.getScore(), a.getScore()));
        return ranked.subList(0, Math.min(limit, ranked.size()));
    }
}
