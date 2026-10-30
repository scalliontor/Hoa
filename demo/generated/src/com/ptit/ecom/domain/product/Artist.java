package com.ptit.ecom.domain.product;

/**
 * Painter of a painting (painting-shop domain model).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Artist {
    private String artistId;
    private String name;
    private String nationality;
    private String lifeYears;

    public String getDisplayName() {
        return lifeYears == null ? name : name + " (" + lifeYears + ")";
    }

    public String getArtistId() {
        return artistId;
    }

    public void setArtistId(String artistId) {
        this.artistId = artistId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getNationality() {
        return nationality;
    }

    public void setNationality(String nationality) {
        this.nationality = nationality;
    }

    public String getLifeYears() {
        return lifeYears;
    }

    public void setLifeYears(String lifeYears) {
        this.lifeYears = lifeYears;
    }
}
