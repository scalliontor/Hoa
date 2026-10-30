public class SearchService {
    // ... (other members omitted)
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
}
