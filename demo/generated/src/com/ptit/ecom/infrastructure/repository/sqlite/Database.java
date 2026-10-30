package com.ptit.ecom.infrastructure.repository.sqlite;

import java.sql.Connection;

/**
 * SQLite database ecom.db (Infrastructure layer, slide A05).
 * Generated from the 4.4 design model (tools/model.py).
 */
public class Database {
    private String url;

    public Database(String url) {
        throw new UnsupportedOperationException("TODO: Database");
    }

    public Connection getConnection() {
        throw new UnsupportedOperationException("TODO: getConnection");
    }

    public void initialize(String schemaSql, String seedSql) {
        throw new UnsupportedOperationException("TODO: initialize");
    }
}
