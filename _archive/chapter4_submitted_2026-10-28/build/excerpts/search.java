public class SearchService {
    // ... fields, constructor, searchText and searchVoice omitted

    public List<SearchResult> searchImage(byte[] image) {
        CommonQuery query = queryService.buildImageQuery(vectorIndex.embed(image));
        List<SearchResult> candidates = new ArrayList<>();
        for (Map.Entry<String, Double> hit : vectorIndex.nearest(query.getImageVector(), 20).entrySet()) {
            Product product = productDAO.findById(hit.getKey());
            if (product != null) candidates.add(new SearchResult(product, hit.getValue()));
        }
        return rankingService.rank(query, candidates, 5);
    }
}

public class SearchController {
    // ... field and constructor omitted

    public List<SearchResult> search(String mode, String text, byte[] image) {
        if ("voice".equals(mode)) return searchService.searchVoice(text);
        if ("image".equals(mode)) return searchService.searchImage(image);
        return searchService.searchText(text);
    }
}
