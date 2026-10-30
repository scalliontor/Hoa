package com.ptit.ecom.domain.product;

/**
 * Painting sold by the shop, a specialisation of Product (domain model 4.1).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Painting extends Product {
    private String style;
    private String subject;
    private String dominantColor;
    private String medium;
    private int yearCreated;
    private int widthCm;
    private int heightCm;
    private Artist artist;

    @Override
    public String getCategory() {
        return "PAINTING";
    }

    @Override
    public String keywords() {
        StringBuilder text = new StringBuilder(super.keywords());
        for (String part : new String[] {style, subject, dominantColor, medium, artist == null ? null : artist.getName()}) {
            if (part != null) text.append(' ').append(part.toLowerCase());
        }
        return text.toString();
    }

    public String sizeLabel() {
        return widthCm + " x " + heightCm + " cm";
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

    public String getDominantColor() {
        return dominantColor;
    }

    public void setDominantColor(String dominantColor) {
        this.dominantColor = dominantColor;
    }

    public String getMedium() {
        return medium;
    }

    public void setMedium(String medium) {
        this.medium = medium;
    }

    public int getYearCreated() {
        return yearCreated;
    }

    public void setYearCreated(int yearCreated) {
        this.yearCreated = yearCreated;
    }

    public int getWidthCm() {
        return widthCm;
    }

    public void setWidthCm(int widthCm) {
        this.widthCm = widthCm;
    }

    public int getHeightCm() {
        return heightCm;
    }

    public void setHeightCm(int heightCm) {
        this.heightCm = heightCm;
    }

    public Artist getArtist() {
        return artist;
    }

    public void setArtist(Artist artist) {
        this.artist = artist;
    }
}
