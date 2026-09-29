package br.com.ilan.tcc.core;

import java.util.UUID;

/** Request/record correlation is metadata, never part of the event hash. */
public final class RunContext {
    private static final ThreadLocal<String> RUN_ID = new ThreadLocal<>();
    private static final ThreadLocal<String> VARIANT = new ThreadLocal<>();

    private RunContext() {}

    public static String validate(String value) {
        return value == null || value.isEmpty() ? null : UUID.fromString(value).toString();
    }

    public static void set(String runId, String variant) {
        RUN_ID.set(runId);
        VARIANT.set(variant);
    }

    public static String runId() { return RUN_ID.get(); }
    public static String variant() { return VARIANT.get(); }

    public static void clear() {
        RUN_ID.remove();
        VARIANT.remove();
    }
}
