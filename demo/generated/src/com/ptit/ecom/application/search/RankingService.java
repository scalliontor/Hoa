package com.ptit.ecom.application.search;

import com.ptit.ecom.domain.product.Product;
import java.util.List;

/**
 * RankingService of slide A06: S = a*Stext + b*Simage + c*Sbusiness.
 * Generated from the 4.4 design model (tools/model.py).
 */
public class RankingService {
    private double alpha;
    private double beta;
    private double gamma;

    public RankingService(double alpha, double beta, double gamma) {
        throw new UnsupportedOperationException("TODO: RankingService");
    }

    public List<SearchResult> rank(CommonQuery query, List<SearchResult> candidates, int limit) {
        throw new UnsupportedOperationException("TODO: rank");
    }

    public double businessScore(Product product) {
        throw new UnsupportedOperationException("TODO: businessScore");
    }
}
