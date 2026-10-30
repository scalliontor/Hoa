package com.ptit.ecom.domain.payment;

/**
 * Card payment: only the last four digits and the authorisation code are kept (NFR05).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class PayCredit extends Payment {
    private String cardHolder;
    private String bankName;
    private String cardLast4;
    private String authorizationCode;

    @Override
    public boolean process() {
        // The card is authorised by the payment provider; only its code is kept here.
        if (authorizationCode == null || authorizationCode.trim().isEmpty()) {
            markFailed();
            return false;
        }
        markSucceeded();
        return true;
    }

    public String maskedCard() {
        return "**** **** **** " + cardLast4;
    }

    public String getCardHolder() {
        return cardHolder;
    }

    public void setCardHolder(String cardHolder) {
        this.cardHolder = cardHolder;
    }

    public String getBankName() {
        return bankName;
    }

    public void setBankName(String bankName) {
        this.bankName = bankName;
    }

    public String getCardLast4() {
        return cardLast4;
    }

    public void setCardLast4(String cardLast4) {
        this.cardLast4 = cardLast4;
    }

    public String getAuthorizationCode() {
        return authorizationCode;
    }

    public void setAuthorizationCode(String authorizationCode) {
        this.authorizationCode = authorizationCode;
    }
}
