package com.ptit.ecom.domain.customer;

/**
 * Generated from the Chapter 4.4 design model (tools/model.py).
 * Value object: Vietnamese order is last + middle + first name.
 */
public class FullName {
    private String firstName;
    private String middleName;
    private String lastName;

    public String getDisplayName() {
        StringBuilder sb = new StringBuilder();
        for (String part : new String[] {lastName, middleName, firstName}) {
            if (part != null && !part.trim().isEmpty()) {
                if (sb.length() > 0) sb.append(' ');
                sb.append(part.trim());
            }
        }
        return sb.toString();
    }

    public String getFirstName() {
        return firstName;
    }

    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public String getMiddleName() {
        return middleName;
    }

    public void setMiddleName(String middleName) {
        this.middleName = middleName;
    }

    public String getLastName() {
        return lastName;
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }
}
