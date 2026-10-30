package com.ptit.ecom.test;

import java.math.BigDecimal;
import java.util.Objects;

/**
 * Runs all tests of the demo without a test framework: one PASS/FAIL line per test (Chapter 5).
 * The exit code is 1 when a test fails, so test.sh can stop.
 */
public final class TestRunner {
    interface Body {
        void run() throws Exception;
    }

    private static int passed;
    private static int failed;

    public static void main(String[] args) throws Exception {
        section("Domain rules (4.1, 4.3)", DomainTest::run);
        section("Repositories and seed data (4.2)", RepositoryTest::run);
        section("Checkout (slide A05)", CheckoutTest::run);
        section("Orders: ownership, cancel, status (NFR01, UC11, UC13)", OrderServiceTest::run);
        section("Search and ranking (slide A06)", SearchTest::run);
        section("Assistant with tool calling (UC10)", AssistantTest::run);
        section("Vocabulary shared by prompts, VectorIndex and the database", VocabularyTest::run);
        section("HTTP API (WebServer)", WebServerTest::run);
        System.out.println();
        System.out.println(passed + " tests passed, " + failed + " failed");
        System.exit(failed == 0 ? 0 : 1);
    }

    private static void section(String title, Body tests) throws Exception {
        System.out.println();
        System.out.println("== " + title);
        tests.run();
    }

    static void test(String name, Body body) {
        try {
            body.run();
            passed++;
            System.out.println("PASS  " + name);
        } catch (Throwable e) {
            failed++;
            System.out.println("FAIL  " + name + " -> " + e);
        }
    }

    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    static void same(Object expected, Object actual, String what) {
        if (!Objects.equals(expected, actual)) {
            throw new AssertionError(what + ": expected " + expected + " but was " + actual);
        }
    }

    static void money(String expected, BigDecimal actual, String what) {
        if (actual == null || actual.compareTo(new BigDecimal(expected)) != 0) {
            throw new AssertionError(what + ": expected " + expected + " but was " + actual);
        }
    }

    static <T extends Throwable> T fails(Class<T> type, Body body) {
        try {
            body.run();
        } catch (Throwable e) {
            if (type.isInstance(e)) return type.cast(e);
            throw new AssertionError("expected " + type.getSimpleName() + " but got " + e, e);
        }
        throw new AssertionError("expected " + type.getSimpleName() + " but nothing was thrown");
    }
}
