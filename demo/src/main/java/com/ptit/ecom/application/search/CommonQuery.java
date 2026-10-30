package com.ptit.ecom.application.search;

import java.math.BigDecimal;

/**
 * Common query representation for text, voice and image (slide A06).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class CommonQuery {
    private String type;
    private String query;
    private double[] embedding;
    private String style;
    private String subject;
    private String color;
    private String artist;
    private BigDecimal maxPrice;
    private boolean aiUsed;

    public CommonQuery(String type, String query) {
        this.type = type;
        this.query = query;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getQuery() {
        return query;
    }

    public void setQuery(String query) {
        this.query = query;
    }

    public double[] getEmbedding() {
        return embedding;
    }

    public void setEmbedding(double[] embedding) {
        this.embedding = embedding;
    }

    public String getStyle() {
        return style;
    }

    public void setStyle(String style) {
        this.style = style;
    }

    public String getSubject() {
        return subject;
    }

    public void setSubject(String subject) {
        this.subject = subject;
    }

    public String getColor() {
        return color;
    }

    public void setColor(String color) {
        this.color = color;
    }

    public String getArtist() {
        return artist;
    }

    public void setArtist(String artist) {
        this.artist = artist;
    }

    public BigDecimal getMaxPrice() {
        return maxPrice;
    }

    public void setMaxPrice(BigDecimal maxPrice) {
        this.maxPrice = maxPrice;
    }

    public boolean getAiUsed() {
        return aiUsed;
    }

    public void setAiUsed(boolean aiUsed) {
        this.aiUsed = aiUsed;
    }
}
