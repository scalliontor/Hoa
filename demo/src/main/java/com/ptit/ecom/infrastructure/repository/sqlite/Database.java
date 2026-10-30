package com.ptit.ecom.infrastructure.repository.sqlite;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * SQLite database ecom.db (Infrastructure layer, slide A05).
 * The schema and the sample data come from db/ecom_schema_sqlite.sql and db/seed.sql.
 */
public class Database {
    private String url;

    public Database(String url) {
        this.url = url;
    }

    /** Every connection turns foreign-key checks on, because SQLite leaves them off by default. */
    public Connection getConnection() {
        try {
            Connection connection = DriverManager.getConnection(url);
            try (Statement statement = connection.createStatement()) {
                statement.execute("PRAGMA foreign_keys = ON");
            }
            return connection;
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot open database " + url, e);
        }
    }

    /** The first run creates the tables and loads the sample data; later runs keep the existing data. */
    public void initialize(String schemaSql, String seedSql) {
        try (Connection connection = getConnection()) {
            if (hasTables(connection)) return;
            connection.setAutoCommit(false);
            runScript(connection, schemaSql);
            runScript(connection, seedSql);
            connection.commit();
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot initialise the database", e);
        }
    }

    private boolean hasTables(Connection connection) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet rows = statement.executeQuery(
                     "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'product'")) {
            return rows.next();
        }
    }

    /** Runs every statement of a .sql file; each statement ends with ; at the end of a line. */
    private void runScript(Connection connection, String script) throws SQLException {
        try (Statement statement = connection.createStatement()) {
            for (String sql : script.split(";\\s*\\n")) {
                if (!sql.replaceAll("--[^\\n]*", "").trim().isEmpty()) statement.execute(sql);
            }
        }
    }
}
