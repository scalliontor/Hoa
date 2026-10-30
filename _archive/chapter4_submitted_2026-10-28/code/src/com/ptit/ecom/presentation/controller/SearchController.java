package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.search.SearchResult;
import com.ptit.ecom.application.search.SearchService;
import java.util.List;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class SearchController {
    private SearchService searchService;

    public SearchController(SearchService searchService) {
        this.searchService = searchService;
    }

    public List<SearchResult> search(String mode, String text, byte[] image) {
        if ("voice".equals(mode)) return searchService.searchVoice(text);
        if ("image".equals(mode)) return searchService.searchImage(image);
        return searchService.searchText(text);
    }
}
