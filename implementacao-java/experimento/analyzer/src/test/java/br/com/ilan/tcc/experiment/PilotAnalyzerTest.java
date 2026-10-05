package br.com.ilan.tcc.experiment;

import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class PilotAnalyzerTest {
    private static final String RUN = "123e4567-e89b-12d3-a456-426614174000";
    private static final String EVENT = "123e4567-e89b-12d3-a456-000000000000";
    // SHA-256 of the sorted pilot JSON, computed independently of the analyzer.
    private static final String HASH = "605cb08fe98bad5dd7b863c5ac352cf33d3aec943a5d8785022cf0edf11663e1";
    @TempDir Path temp;

    @Test void reconcilesSyncAndMeasuresCommitSeparately() throws Exception {
        var result = analyze("sync", fixture("sync", 201, "153", "143", row(), "", ""));
        assertTrue(result.valid(), result.summary().toString());
        assertEquals(1, result.summary().get("database_content_matches"));
        assertEquals(30.0, metric(result, "send_to_response_ms").get("mean"));
        assertEquals(20.0, metric(result, "send_to_commit_ms").get("mean"));
        assertEquals(28.0, metric(result, "http_duration_ms").get("mean"));
    }

    @Test void asyncAcceptanceIsNotCompletion() throws Exception {
        var result = analyze("async", fixture("async", 202, "133", "223", row(), "", ""));
        assertTrue(result.valid());
        assertEquals(10.0, metric(result, "send_to_response_ms").get("mean"));
        assertEquals(100.0, metric(result, "send_to_commit_ms").get("mean"));
    }

    @Test void missingDatabaseEvidenceIsNotCalledLoss() throws Exception {
        var result = analyze("async", fixture("async", 202, "133", "223", "", "", ""));
        assertFalse(result.valid());
        assertTrue(issues(result).contains(EVENT + ":completion_not_reconciled"));
        assertFalse(issues(result).stream().anyMatch(issue -> issue.contains("loss")));
    }

    @Test void detectsContentAndHashChanges() throws Exception {
        for (String wrong : List.of(row().replace("\"value\":0", "\"value\":9"), row().replace(HASH, "0".repeat(64)))) {
            var result = analyze("sync", fixture("sync", 201, "153", "143", wrong, "", ""));
            assertFalse(result.valid());
            assertTrue(issues(result).contains(EVENT + ":database_content_mismatch"));
        }
    }

    @Test void detectsNegativeCrossProcessInterval() throws Exception {
        var result = analyze("sync", fixture("sync", 201, "153", "122", row(), "", ""));
        assertFalse(result.valid());
        assertTrue(issues(result).contains(EVENT + ":negative_commit_interval_clock_or_collection_error"));
    }

    @Test void detectsRepeatedCommitRatherThanHidingIt() throws Exception {
        var result = analyze("sync", fixture("sync", 201, "153", "143", row(), "", commit("sync", "144")));
        assertFalse(result.valid());
        assertTrue(issues(result).contains(EVENT + ":multiple_commit_markers"));
    }

    @Test void detectsDroppedIterations() throws Exception {
        String point = point("dropped_iterations", "123", "sync", "", "1");
        var result = analyze("sync", fixture("sync", 201, "153", "143", row(), point, ""));
        assertFalse(result.valid());
        assertEquals(1.0, result.summary().get("dropped_iterations"));
    }

    @Test void skipsReadinessAndOtherRuns() throws Exception {
        String extra = point("http_req_duration", "123", "sync", ",\"phase\":\"readiness\"", "1")
            + point("pilot_sent", "123", "sync", "", "1").replace(RUN, "223e4567-e89b-12d3-a456-426614174000");
        var result = analyze("sync", fixture("sync", 201, "153", "143", row(), extra,
            commit("sync", "144").replace(RUN, "223e4567-e89b-12d3-a456-426614174000")));
        assertTrue(result.valid(), result.summary().toString());
        assertEquals(1, result.summary().get("events_observed"));
    }

    @Test void detectsDuplicateDatabaseRows() throws Exception {
        var result = analyze("sync", fixture("sync", 201, "153", "143", row() + row(), "", ""));
        assertFalse(result.valid());
        assertTrue(issues(result).contains(EVENT + ":duplicate_database_row"));
    }

    @Test void rejectsUnexpectedHttpStatus() throws Exception {
        var result = analyze("sync", fixture("sync", 500, "153", "143", row(), "", ""));
        assertFalse(result.valid());
        assertEquals(0, result.summary().get("expected_responses"));
    }

    @Test void rejectsVariantMismatch() throws Exception {
        var result = analyze("async", fixture("sync", 201, "153", "143", row(), "", ""));
        assertFalse(result.valid());
        assertTrue(issues(result).contains("k6_variant_mismatch"));
    }

    @Test void rejectsEmptyEvidence() throws Exception {
        var result = analyze("sync", fixture("sync", 201, "153", "143", "", "", ""));
        Files.writeString(temp.resolve("k6.jsonl"), "");
        Files.writeString(temp.resolve("app.log"), "");
        result = analyze("sync", new Evidence(temp.resolve("k6.jsonl"), temp.resolve("app.log"), temp.resolve("database.jsonl")));
        assertFalse(result.valid());
        assertTrue(issues(result).contains("no_events"));
    }

    @Test void malformedInputFailsClosed() throws Exception {
        var evidence = fixture("sync", 201, "153", "143", row(), "{not_json}\n", "");
        assertThrows(java.io.IOException.class, () -> analyze("sync", evidence));
    }

    private PilotAnalyzer.Analysis analyze(String variant, Evidence evidence) throws Exception {
        return PilotAnalyzer.analyze(RUN, variant, evidence.k6(), evidence.logs(), evidence.database());
    }

    private Evidence fixture(String variant, int status, String reply, String committed, String database,
                             String extraK6, String extraLogs) throws Exception {
        Path k6 = temp.resolve("k6.jsonl");
        Path logs = temp.resolve("app.log");
        Path db = temp.resolve("database.jsonl");
        Files.writeString(k6, point("pilot_sent", "123", variant,
            ",\"event_id\":\"" + EVENT + "\",\"iteration\":\"0\",\"occurred_at\":\"2026-10-05T12:00:00.123Z\"", "1")
            + point("pilot_response", reply, variant,
                ",\"event_id\":\"" + EVENT + "\",\"http_status\":\"" + status + "\",\"id_matches\":\"true\"", "1")
            + point("http_req_duration", reply, variant, ",\"event_id\":\"" + EVENT + "\"", "28") + extraK6);
        Files.writeString(logs, "sync-api-1 | " + commit(variant, committed) + extraLogs);
        Files.writeString(db, database);
        return new Evidence(k6, logs, db);
    }

    private static String point(String metric, String millis, String variant, String tags, String value) {
        return "{\"type\":\"Point\",\"metric\":\"" + metric + "\",\"data\":{\"time\":\"2026-10-05T12:00:00."
            + millis + "Z\",\"value\":" + value + ",\"tags\":{\"run_id\":\"" + RUN + "\",\"variant\":\"" + variant + "\"" + tags + "}}}\n";
    }

    private static String commit(String variant, String millis) {
        return "{\"milestone\":\"commit_completed\",\"timestamp\":\"2026-10-05T12:00:00." + millis
            + "Z\",\"run_id\":\"" + RUN + "\",\"variant\":\"" + variant + "\",\"event_id\":\"" + EVENT + "\",\"status\":\"persisted\"}\n";
    }

    private static String row() {
        return "{\"event_id\":\"" + EVENT + "\",\"event_type\":\"created\",\"entity_type\":\"pilot\",\"entity_id\":\"E0\","
            + "\"actor_id\":\"k6-pilot\",\"source\":\"k6-pilot-" + RUN + "\",\"occurred_at\":\"2026-10-05T12:00:00.123+00:00\","
            + "\"payload\":{\"value\":0},\"content_hash\":\"" + HASH + "\"}\n";
    }

    @SuppressWarnings("unchecked") private static List<String> issues(PilotAnalyzer.Analysis result) {
        return (List<String>) result.summary().get("issues");
    }

    @SuppressWarnings("unchecked") private static Map<String, Object> metric(PilotAnalyzer.Analysis result, String name) {
        return (Map<String, Object>) result.summary().get(name);
    }

    private record Evidence(Path k6, Path logs, Path database) {}
}
