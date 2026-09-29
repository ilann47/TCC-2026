package br.com.ilan.tcc.core;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** One JSON line per measurement milestone; payloads and credentials are excluded. */
public final class MilestoneLog {
    private static final Set<String> ALLOWED = Set.of("event_id", "status", "reason", "attempt",
        "delay_seconds", "topic", "partition", "offset", "duration_ms", "persisted_at");

    private MilestoneLog() {}

    public static void emit(String milestone, Object... fields) {
        if (fields.length % 2 != 0) throw new IllegalArgumentException("odd_milestone_fields");
        Instant now = Instant.now();
        Map<String, Object> line = new LinkedHashMap<>();
        line.put("milestone", milestone);
        line.put("timestamp", OffsetDateTime.ofInstant(now, ZoneOffset.UTC).toString());
        line.put("wall_time_ns", now.getEpochSecond() * 1_000_000_000L + now.getNano());
        line.put("monotonic_ns", System.nanoTime());
        line.put("run_id", RunContext.runId());
        line.put("variant", RunContext.variant());
        for (int i = 0; i < fields.length; i += 2) {
            String key = (String) fields[i];
            if (ALLOWED.contains(key)) {
                Object value = fields[i + 1];
                line.put(key, value instanceof java.util.UUID || value instanceof OffsetDateTime
                    ? value.toString() : value);
            }
        }
        try {
            System.out.println(CanonicalEventCodec.mapper().writeValueAsString(line));
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new IllegalStateException("milestone_serialization_failed", ex);
        }
    }
}
