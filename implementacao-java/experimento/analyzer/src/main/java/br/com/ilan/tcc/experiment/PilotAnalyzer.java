package br.com.ilan.tcc.experiment;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Locale;
import java.util.TreeMap;
import java.util.UUID;

/** Reconciles a small measurement pilot; missing evidence is never called loss. */
public final class PilotAnalyzer {
    private static final ObjectMapper JSON = new ObjectMapper();

    private PilotAnalyzer() {}

    public static void main(String[] args) throws IOException {
        if (args.length != 6) {
            throw new IllegalArgumentException("Usage: <run UUID> <sync|async> <k6.jsonl> <app.log> <database.jsonl> <output dir>");
        }
        var result = analyze(args[0], args[1], Path.of(args[2]), Path.of(args[3]), Path.of(args[4]));
        write(result, Path.of(args[5]));
        System.out.println(JSON.writeValueAsString(result.summary()));
        if (!result.valid()) System.exit(2);
    }

    static Analysis analyze(String runId, String variant, Path k6, Path logs, Path database) throws IOException {
        UUID.fromString(runId);
        if (!List.of("sync", "async").contains(variant)) throw new IllegalArgumentException("invalid variant");
        Map<String, Event> events = new LinkedHashMap<>();
        List<String> issues = new ArrayList<>();
        double dropped = readK6(k6, runId, variant, events, issues);
        readLogs(logs, runId, variant, events, issues);
        readDatabase(database, events, issues);
        if (events.isEmpty()) issues.add("no_events");
        if (dropped != 0) issues.add("dropped_iterations=" + dropped);

        int accepted = 0;
        int databaseRecords = 0;
        int completed = 0;
        int integrityMatches = 0;
        int expectedStatus = variant.equals("sync") ? 201 : 202;
        List<Double> http = new ArrayList<>();
        List<Double> response = new ArrayList<>();
        List<Double> completion = new ArrayList<>();
        for (Event event : events.values()) {
            if (event.sentAt == null || event.responseAt == null || event.httpMs == null) {
                issues.add(event.id + ":incomplete_client_evidence");
            }
            if (event.httpStatus == expectedStatus && event.idMatches) accepted++;
            else issues.add(event.id + ":unexpected_response_" + event.httpStatus);
            if (event.database != null) databaseRecords++;
            if (event.database != null && matchesInput(event, runId)) integrityMatches++;
            else if (event.database != null) issues.add(event.id + ":database_content_mismatch");
            if (event.commitAt != null && event.database != null && "persisted".equals(event.commitStatus)) completed++;
            else issues.add(event.id + ":completion_not_reconciled");
            if (event.dlq) issues.add(event.id + ":dlq_acknowledged");
            if (event.httpMs != null && Double.isFinite(event.httpMs) && event.httpMs >= 0) http.add(event.httpMs);
            else if (event.httpMs != null) issues.add(event.id + ":invalid_http_duration");
            addInterval(event.id, "response", event.sentAt, event.responseAt, response, issues);
            addInterval(event.id, "commit", event.sentAt, event.commitAt, completion, issues);
        }
        var summary = new LinkedHashMap<String, Object>();
        summary.put("kind", "measurement_pilot_not_definitive_experiment");
        summary.put("run_id", runId);
        summary.put("variant", variant);
        summary.put("instrument_valid", issues.isEmpty());
        summary.put("events_observed", events.size());
        summary.put("expected_responses", accepted);
        summary.put("database_records", databaseRecords);
        summary.put("database_content_matches", integrityMatches);
        summary.put("reconciled_completions", completed);
        summary.put("dropped_iterations", dropped);
        summary.put("http_duration_ms", statistics(http));
        summary.put("send_to_response_ms", statistics(response));
        summary.put("send_to_commit_ms", statistics(completion));
        summary.put("issues", issues);
        summary.put("interpretation", "Short local instrumentation check; missing evidence requires investigation, not a claim of data loss. Cross-process intervals use wall clocks; generator tags and observation add overhead.");
        return new Analysis(summary, events, issues.isEmpty());
    }

    private static double readK6(Path file, String runId, String variant, Map<String, Event> events,
                                 List<String> issues) throws IOException {
        double dropped = 0;
        try (var lines = Files.lines(file, StandardCharsets.UTF_8)) {
            for (String line : (Iterable<String>) lines::iterator) {
                if (line.isBlank()) continue;
                JsonNode root = JSON.readTree(line);
                if (!"Point".equals(root.path("type").asText())) continue;
                JsonNode data = root.path("data");
                JsonNode tags = data.path("tags");
                if (!runId.equals(tags.path("run_id").asText())) continue;
                if (!variant.equals(tags.path("variant").asText())) {
                    issues.add("k6_variant_mismatch");
                    continue;
                }
                String metric = root.path("metric").asText();
                if ("readiness".equals(tags.path("phase").asText())) continue;
                if (metric.equals("dropped_iterations")) {
                    dropped += data.path("value").asDouble();
                    continue;
                }
                if (!List.of("pilot_sent", "pilot_response", "http_req_duration").contains(metric)) continue;
                String id = tags.path("event_id").asText();
                UUID.fromString(id);
                Event event = events.computeIfAbsent(id, Event::new);
                Instant at = instant(data.path("time").asText());
                switch (metric) {
                    case "pilot_sent" -> {
                        if (event.sentAt != null) issues.add(id + ":duplicate_send_marker");
                        event.sentAt = at;
                        event.iteration = Long.parseLong(tags.path("iteration").asText());
                        event.occurredAt = instant(tags.path("occurred_at").asText());
                    }
                    case "pilot_response" -> {
                        if (event.responseAt != null) issues.add(id + ":duplicate_response_marker");
                        event.responseAt = at;
                        event.httpStatus = Integer.parseInt(tags.path("http_status").asText());
                        event.idMatches = "true".equals(tags.path("id_matches").asText());
                    }
                    case "http_req_duration" -> {
                        if (event.httpMs != null) issues.add(id + ":duplicate_http_marker");
                        event.httpMs = data.path("value").asDouble();
                    }
                    default -> throw new IllegalStateException("unexpected metric");
                }
            }
        }
        return dropped;
    }

    private static void readLogs(Path file, String runId, String variant, Map<String, Event> events,
                                  List<String> issues) throws IOException {
        try (var lines = Files.lines(file, StandardCharsets.UTF_8)) {
            for (String line : (Iterable<String>) lines::iterator) {
                int brace = line.indexOf('{');
                if (brace < 0 || !line.contains("\"milestone\"")) continue;
                JsonNode root = JSON.readTree(line.substring(brace));
                if (!runId.equals(root.path("run_id").asText())) continue;
                String milestone = root.path("milestone").asText();
                if (!List.of("commit_completed", "dlq_acknowledged").contains(milestone)) continue;
                String id = root.path("event_id").asText();
                Event event = events.get(id);
                if (event == null) {
                    issues.add(id + ":server_event_without_client_evidence");
                    continue;
                }
                if (!variant.equals(root.path("variant").asText())) issues.add(id + ":server_variant_mismatch");
                if (milestone.equals("dlq_acknowledged")) event.dlq = true;
                else {
                    if (event.commitAt != null) issues.add(id + ":multiple_commit_markers");
                    else {
                        event.commitAt = instant(root.path("timestamp").asText());
                        event.commitStatus = root.path("status").asText();
                    }
                }
            }
        }
    }

    private static void readDatabase(Path file, Map<String, Event> events, List<String> issues) throws IOException {
        try (var lines = Files.lines(file, StandardCharsets.UTF_8)) {
            for (String line : (Iterable<String>) lines::iterator) {
                if (line.isBlank()) continue;
                JsonNode row = JSON.readTree(line);
                String id = row.path("event_id").asText();
                Event event = events.get(id);
                if (event == null) issues.add(id + ":database_event_without_client_evidence");
                else if (event.database != null) issues.add(id + ":duplicate_database_row");
                else event.database = row;
            }
        }
    }

    private static boolean matchesInput(Event event, String runId) {
        JsonNode row = event.database;
        return event.occurredAt != null
            && "created".equals(row.path("event_type").asText())
            && "pilot".equals(row.path("entity_type").asText())
            && ("E" + event.iteration).equals(row.path("entity_id").asText())
            && "k6-pilot".equals(row.path("actor_id").asText())
            && ("k6-pilot-" + runId).equals(row.path("source").asText())
            && event.occurredAt.equals(instant(row.path("occurred_at").asText()))
            && row.path("payload").isObject() && row.path("payload").size() == 1
            && row.path("payload").path("value").isIntegralNumber()
            && row.path("payload").path("value").asLong(-1) == event.iteration % 10
            && row.path("content_hash").asText().equals(expectedHash(event, runId));
    }

    // Independent, deliberately narrow encoder for the pilot's fixed integer payload.
    // It does not call the production codec, so a change to that codec is observable.
    private static String expectedHash(Event event, String runId) {
        var at = event.occurredAt.atOffset(ZoneOffset.UTC);
        String time = at.format(DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss", Locale.ROOT));
        int micros = at.getNano() / 1_000;
        if (micros != 0) time += String.format(Locale.ROOT, ".%06d", micros);
        var fields = new TreeMap<String, Object>();
        fields.put("actor_id", "k6-pilot");
        fields.put("entity_id", "E" + event.iteration);
        fields.put("entity_type", "pilot");
        fields.put("event_id", event.id);
        fields.put("event_type", "created");
        fields.put("occurred_at", time + "Z");
        fields.put("payload", Map.of("value", event.iteration % 10));
        fields.put("source", "k6-pilot-" + runId);
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(JSON.writeValueAsBytes(fields)));
        } catch (IOException | NoSuchAlgorithmException ex) {
            throw new IllegalStateException("cannot_hash_expected_pilot_content", ex);
        }
    }

    private static void addInterval(String id, String name, Instant start, Instant end, List<Double> samples,
                                     List<String> issues) {
        if (start == null || end == null) return;
        double ms = Duration.between(start, end).toNanos() / 1_000_000.0;
        if (ms < 0) issues.add(id + ":negative_" + name + "_interval_clock_or_collection_error");
        else samples.add(ms);
    }

    private static Instant instant(String value) { return OffsetDateTime.parse(value).toInstant(); }

    private static Map<String, Object> statistics(List<Double> samples) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("n", samples.size());
        if (!samples.isEmpty()) {
            List<Double> sorted = samples.stream().sorted().toList();
            result.put("mean", samples.stream().mapToDouble(Double::doubleValue).average().orElseThrow());
            result.put("p50_nearest_rank", sorted.get((int) Math.ceil(sorted.size() * 0.50) - 1));
            result.put("p95_nearest_rank", sorted.get((int) Math.ceil(sorted.size() * 0.95) - 1));
            result.put("p99_nearest_rank", sorted.get((int) Math.ceil(sorted.size() * 0.99) - 1));
        }
        return result;
    }

    private static void write(Analysis analysis, Path output) throws IOException {
        Files.createDirectories(output);
        JSON.writerWithDefaultPrettyPrinter().writeValue(output.resolve("summary.json").toFile(), analysis.summary());
        try (var writer = Files.newBufferedWriter(output.resolve("events.csv"), StandardCharsets.UTF_8)) {
            writer.write("event_id,http_status,id_matches,http_duration_ms,send_to_response_ms,send_to_commit_ms,commit_status,db_present,dlq\n");
            for (Event event : analysis.events().values()) {
                writer.write(String.join(",", event.id, Integer.toString(event.httpStatus), Boolean.toString(event.idMatches),
                    event.httpMs == null ? "" : event.httpMs.toString(), interval(event.sentAt, event.responseAt),
                    interval(event.sentAt, event.commitAt), event.commitStatus == null ? "" : event.commitStatus,
                    Boolean.toString(event.database != null), Boolean.toString(event.dlq)) + "\n");
            }
        }
    }

    private static String interval(Instant start, Instant end) {
        return start == null || end == null ? "" : Double.toString(Duration.between(start, end).toNanos() / 1_000_000.0);
    }

    record Analysis(Map<String, Object> summary, Map<String, Event> events, boolean valid) {}

    static final class Event {
        final String id;
        Instant sentAt;
        Instant occurredAt;
        Instant responseAt;
        Instant commitAt;
        long iteration;
        int httpStatus;
        boolean idMatches;
        Double httpMs;
        String commitStatus;
        boolean dlq;
        JsonNode database;
        Event(String id) { this.id = id; }
    }
}
