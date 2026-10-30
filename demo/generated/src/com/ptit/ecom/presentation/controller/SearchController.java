package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.search.SearchResult;
import com.ptit.ecom.application.search.SearchService;
import com.ptit.ecom.application.search.SpeechService;
import java.util.List;
import java.util.Map;

/**
 * Search controller (slide A05: a Controller receives requests).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class SearchController {
    private SearchService searchService;
    private SpeechService speechService;

    public SearchController(SearchService searchService, SpeechService speechService) {
        throw new UnsupportedOperationException("TODO: SearchController");
    }

    public List<SearchResult> search(String text) {
        throw new UnsupportedOperationException("TODO: search");
    }

    public String transcribe(byte[] audioInput) {
        throw new UnsupportedOperationException("TODO: transcribe");
    }

    public List<SearchResult> searchVoice(String transcript) {
        throw new UnsupportedOperationException("TODO: searchVoice");
    }

    public List<SearchResult> searchImage(byte[] image) {
        throw new UnsupportedOperationException("TODO: searchImage");
    }

    public List<SearchResult> searchRoom(byte[] image) {
        throw new UnsupportedOperationException("TODO: searchRoom");
    }

    public Map<String, String> describeRoom(byte[] image) {
        throw new UnsupportedOperationException("TODO: describeRoom");
    }

    public List<SearchResult> searchMultimodal(String text, byte[] image) {
        throw new UnsupportedOperationException("TODO: searchMultimodal");
    }
}
