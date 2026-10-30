package com.ptit.ecom.domain.product;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class Laptop extends Electronics {
    private String cpu;
    private String ram;
    private String storage;
    private double screenSize;

    @Override
    public String getCategory() {
        return "LAPTOP";
    }

    public String getCpu() {
        return cpu;
    }

    public void setCpu(String cpu) {
        this.cpu = cpu;
    }

    public String getRam() {
        return ram;
    }

    public void setRam(String ram) {
        this.ram = ram;
    }

    public String getStorage() {
        return storage;
    }

    public void setStorage(String storage) {
        this.storage = storage;
    }

    public double getScreenSize() {
        return screenSize;
    }

    public void setScreenSize(double screenSize) {
        this.screenSize = screenSize;
    }
}
