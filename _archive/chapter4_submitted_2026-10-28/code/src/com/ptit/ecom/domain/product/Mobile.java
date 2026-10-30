package com.ptit.ecom.domain.product;

/** Generated from the Chapter 4.4 design model (tools/model.py). */
public class Mobile extends Electronics {
    private String os;
    private String camera;
    private double screenSize;
    private int batteryCapacity;

    @Override
    public String getCategory() {
        return "MOBILE";
    }

    public String getOs() {
        return os;
    }

    public void setOs(String os) {
        this.os = os;
    }

    public String getCamera() {
        return camera;
    }

    public void setCamera(String camera) {
        this.camera = camera;
    }

    public double getScreenSize() {
        return screenSize;
    }

    public void setScreenSize(double screenSize) {
        this.screenSize = screenSize;
    }

    public int getBatteryCapacity() {
        return batteryCapacity;
    }

    public void setBatteryCapacity(int batteryCapacity) {
        this.batteryCapacity = batteryCapacity;
    }
}
