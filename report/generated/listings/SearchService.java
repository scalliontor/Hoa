public class SearchService {
    // ...
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
    // ...
    /** Candidate retrieval: hard price filter, then text and image scores for each product. */
    private List<SearchResult> retrieve(CommonQuery query) {
        List<Product> products = repository.allProducts();
        vectorIndex.build(products);
        Map<String, Double> similar = query.getEmbedding() == null ? Map.of()
                : vectorIndex.nearest(query.getEmbedding(), products.size());
        List<SearchResult> candidates = new ArrayList<>();
        for (Product product : products) {
            if (query.getMaxPrice() != null && product.getPrice().compareTo(query.getMaxPrice()) > 0) continue;
            SearchResult result = new SearchResult(product);
            result.setTextScore(textScore(query, product));
            result.setImageScore(similar.getOrDefault(product.getProductId(), 0.0));
            result.setReason(reason(query, product, result.getImageScore()));
            if (isCandidate(query, result)) candidates.add(result);
        }
        return candidates;
    }
    // ...
}
