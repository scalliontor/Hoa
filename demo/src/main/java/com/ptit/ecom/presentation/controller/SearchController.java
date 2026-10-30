package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.search.SearchResult;
import com.ptit.ecom.application.search.SearchService;
import com.ptit.ecom.application.search.SpeechService;
import java.util.List;
import java.util.Map;

/**
 * Search controller (slide A05: a Controller receives requests).
 * One entry per input mode of slide A06: text, voice (transcribe first), image, room and multimodal.
 */
public class SearchController {
    private SearchService searchService;
    private SpeechService speechService;

    public SearchController(SearchService searchService, SpeechService speechService) {
        this.searchService = searchService;
        this.speechService = speechService;
    }

    public List<SearchResult> search(String text) {
        return searchService.searchText(text);
    }

    /** Whisper transcript, shown to the customer for correction before the voice search runs. */
    public String transcribe(byte[] audioInput) {
        return speechService.transcribe(audioInput);
    }

    public List<SearchResult> searchVoice(String transcript) {
        return searchService.searchVoice(transcript);
    }

    public List<SearchResult> searchImage(byte[] image) {
        return searchService.searchImage(image);
    }

    public List<SearchResult> searchRoom(byte[] image) {
        return searchService.searchRoom(image);
    }

    public Map<String, String> describeRoom(byte[] image) {
        return searchService.describeRoom(image);
    }

    public List<SearchResult> searchMultimodal(String text, byte[] image) {
        return searchService.searchMultimodal(text, image);
    }
}
