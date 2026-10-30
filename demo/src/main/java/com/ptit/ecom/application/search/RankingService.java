package com.ptit.ecom.application.search;

import com.ptit.ecom.domain.product.Product;
import java.util.ArrayList;
import java.util.List;

/**
 * RankingService of slide A06: S = a*Stext + b*Simage + c*Sbusiness.
 * Retrieval finds the candidates; ranking only orders them (slide A06: retrieval and ranking are different).
 */
public class RankingService {
    private double alpha;
    private double beta;
    private double gamma;

    public RankingService(double alpha, double beta, double gamma) {
        this.alpha = alpha;
        this.beta = beta;
        this.gamma = gamma;
    }

    /** S(x|q) = alpha * Stext + beta * Simage + gamma * Sbusiness, highest first. */
    public List<SearchResult> rank(CommonQuery query, List<SearchResult> candidates, int limit) {
        for (SearchResult result : candidates) {
            result.setBusinessScore(businessScore(result.getProduct()));
            result.setScore(alpha * result.getTextScore() + beta * result.getImageScore()
                    + gamma * result.getBusinessScore());
        }
        List<SearchResult> ranked = new ArrayList<>(candidates);
        ranked.sort((a, b) -> Double.compare(b.getScore(), a.getScore()));
        return ranked.subList(0, Math.min(limit, ranked.size()));
    }

    /** Sbusiness: sold-out items sink, items with more stock rise a little. */
    public double businessScore(Product product) {
        if (!product.isAvailable(1)) return 0.0;
        return Math.min(1.0, product.getStockQuantity() / 5.0);
    }
}
