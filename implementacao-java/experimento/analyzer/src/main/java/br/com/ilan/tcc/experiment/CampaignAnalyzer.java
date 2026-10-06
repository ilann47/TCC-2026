package br.com.ilan.tcc.experiment;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Reconciles real runs, including expected HTTP failures, without turning missing data into loss. */
public final class CampaignAnalyzer {
    static final ObjectMapper JSON = new ObjectMapper();
    private CampaignAnalyzer() {}

    public static void main(String[] args) throws IOException {
        if (args.length < 1 || args.length > 2) throw new IllegalArgumentException("campaign <evidence directory> [new analysis directory]");
        Path dir = Path.of(args[0]);
        Path output = args.length == 2 ? Path.of(args[1]) : dir;
        if (Files.exists(output.resolve("summary.json"))) throw new IOException("refusing to overwrite an existing analysis");
        Files.createDirectories(output);
        Map<String, Object> summary = analyze(dir, output);
        JSON.writerWithDefaultPrettyPrinter().writeValue(output.resolve("summary.json").toFile(), summary);
        System.out.println(JSON.writeValueAsString(summary));
        if (!Boolean.TRUE.equals(summary.get("instrument_valid"))) System.exit(2);
    }

    static Map<String, Object> analyze(Path dir) throws IOException {
        return analyze(dir, dir);
    }

    static Map<String, Object> analyze(Path dir, Path output) throws IOException {
        Properties meta = new Properties();
        try (var r = Files.newBufferedReader(dir.resolve("manifest.txt"))) { meta.load(r); }
        String run = meta.getProperty("run_id"), variant = meta.getProperty("variant");
        UUID.fromString(run);
        String dataset = meta.getProperty("dataset_id");
        UUID.fromString(dataset);
        List<String> issues = new ArrayList<>();
        Map<String, Event> events = new LinkedHashMap<>();
        double dropped = 0;
        try (var r = reader(dir.resolve("k6.jsonl.gz"))) {
            String line;
            while ((line = r.readLine()) != null) {
                JsonNode node = JSON.readTree(line), data = node.path("data"), tags = data.path("tags");
                if (!node.path("type").asText().equals("Point") || !run.equals(tags.path("run_id").asText())) continue;
                String metric = node.path("metric").asText();
                if (metric.equals("dropped_iterations")) { dropped += data.path("value").asDouble(); continue; }
                if (!List.of("experiment_sent", "experiment_response", "http_req_duration").contains(metric)
                    || !List.of("warmup", "measure").contains(tags.path("phase").asText())) continue;
                if (!variant.equals(tags.path("variant").asText())) issues.add("variant_mismatch");
                String id = tags.path("event_id").asText();
                UUID.fromString(id);
                Event e = events.computeIfAbsent(id, Event::new);
                e.phase = tags.path("phase").asText();
                Instant time = Instant.parse(data.path("time").asText());
                switch (metric) {
                    case "experiment_sent" -> {
                        if (e.sent != null) issues.add(id + ":duplicate_send");
                        e.sent = time; e.iteration = tags.path("iteration").asLong();
                        e.occurred = Instant.parse(tags.path("occurred_at").asText());
                    }
                    case "experiment_response" -> {
                        if (e.response != null) issues.add(id + ":duplicate_response");
                        e.response = time; e.status = tags.path("http_status").asInt();
                        e.idMatches = tags.path("id_matches").asBoolean();
                    }
                    case "http_req_duration" -> {
                        if (e.http != null) issues.add(id + ":duplicate_http_duration");
                        e.http = data.path("value").asDouble();
                    }
                    default -> throw new IllegalStateException();
                }
            }
        }
        readLines(dir.resolve("app.log"), node -> {
            if (!run.equals(node.path("run_id").asText())) return;
            Event e = events.get(node.path("event_id").asText());
            if (e == null) return;
            String milestone = node.path("milestone").asText();
            switch (milestone) {
                case "commit_completed" -> {
                    Instant at = Instant.parse(node.path("timestamp").asText());
                    if (e.commit == null || at.isBefore(e.commit)) e.commit = at;
                    if (node.path("status").asText().equals("duplicate")) e.replays++;
                    else e.newCommits++;
                }
                case "dlq_acknowledged" -> e.dlqMarker = true;
                case "retry_scheduled" -> e.retries++;
                default -> { }
            }
        });
        readLines(dir.resolve("database.jsonl"), row -> {
            Event e = events.get(row.path("event_id").asText());
            if (e == null) { issues.add("database_without_send"); return; }
            if (e.row != null) issues.add(e.id + ":duplicate_database_row");
            e.row = row;
        });
        Set<String> dlq = new HashSet<>(), retained = new HashSet<>();
        readLines(dir.resolve("dlq.jsonl"), row -> dlq.add(row.path("event_id").asText()));
        readLines(dir.resolve("retained.jsonl"), row -> retained.add(row.path("event_id").asText()));
        double startMs = Double.parseDouble(meta.getProperty("measurement_start_ms"));
        Instant start = Instant.ofEpochMilli((long) startMs);
        int duration = Integer.parseInt(meta.getProperty("measure_seconds"));
        Instant end = start.plusSeconds(duration);
        List<Double> http = new ArrayList<>(), response = new ArrayList<>(), completed = new ArrayList<>();
        Map<String, Integer> statuses = new TreeMap<>();
        int offered = 0, accepted = 0, stored = 0, within = 0, terminal = 0, pending = 0, unresolved = 0;
        int retries = 0, replays = 0, uncertainStored = 0, mismatches = 0, dlqStoredUuid = 0;
        int expected = variant.equals("sync") ? 201 : 202;
        try (var w = Files.newBufferedWriter(output.resolve("events.csv"))) {
            w.write("event_id,phase,http_status,id_matches,http_duration_ms,response_ms,commit_ms,db_present,dlq,pending_retained,retries,idempotent_replays\n");
            for (Event e : events.values()) {
                if (e.sent == null || e.response == null || e.http == null) issues.add(e.id + ":incomplete_client_evidence");
                if (e.http != null && (!Double.isFinite(e.http) || e.http < 0)) issues.add(e.id + ":invalid_http_duration");
                if (e.row != null && !matches(e, dataset)) { issues.add(e.id + ":content_hash_mismatch"); mismatches++; }
                if ((e.commit == null) != (e.row == null)) issues.add(e.id + ":incomplete_commit_db_evidence");
                if (e.newCommits > 1) issues.add(e.id + ":multiple_new_commit_markers");
                if (e.dlqMarker != dlq.contains(e.id)) issues.add(e.id + ":dlq_evidence_mismatch");
                Double r = interval(e.sent, e.response, e.id, issues);
                Double c = interval(e.sent, e.commit, e.id, issues);
                boolean acceptedEvent = e.status == expected && e.idMatches;
                boolean inDlq = dlq.contains(e.id);
                boolean isPending = e.row == null && !inDlq && retained.contains(e.id);
                if (e.phase.equals("measure")) {
                    offered++; statuses.merge(Integer.toString(e.status), 1, Integer::sum);
                    if (e.status == expected && !e.idMatches) issues.add(e.id + ":success_wrong_id");
                    if (acceptedEvent) accepted++;
                    if (e.row != null) { stored++; if (!acceptedEvent) uncertainStored++; }
                    if (e.commit != null && !e.commit.isBefore(start) && e.commit.isBefore(end) && e.row != null) within++;
                    if (inDlq && e.row == null) terminal++;
                    if (inDlq && e.row != null) dlqStoredUuid++;
                    if (isPending) pending++;
                    if (acceptedEvent && e.row == null && !inDlq && !isPending) unresolved++;
                    retries += e.retries; replays += e.replays;
                    if (e.http != null) http.add(e.http);
                    if (r != null) response.add(r);
                    if (c != null && e.row != null) completed.add(c);
                }
                w.write(String.join(",", e.id, e.phase, Integer.toString(e.status), Boolean.toString(e.idMatches),
                    val(e.http), val(r), val(c), Boolean.toString(e.row != null), Boolean.toString(inDlq),
                    Boolean.toString(isPending), Integer.toString(e.retries), Integer.toString(e.replays)) + "\n");
            }
        }
        if (offered == 0) issues.add("no_measured_events");
        // Drops are a separate outcome in overload; invalid calibration is decided by its protocol.
        if (!"0".equals(meta.getProperty("k6_exit"))) issues.add("k6_exit_not_zero");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("kind", meta.getProperty("kind")); out.put("run_id", run); out.put("dataset_id", dataset);
        out.put("variant", variant); out.put("profile", meta.getProperty("profile"));
        out.put("rate", Integer.parseInt(meta.getProperty("rate"))); out.put("measure_seconds", duration);
        out.put("instrument_valid", issues.isEmpty()); out.put("offered", offered); out.put("accepted", accepted);
        out.put("stored_at_observation_end", stored); out.put("stored_within_measurement", within);
        out.put("completed_per_second", within / (double) duration); out.put("http_status_counts", statuses);
        out.put("http_error_fraction", offered == 0 ? null : (offered - accepted) / (double) offered);
        out.put("dropped_iterations_all_phases", dropped); out.put("dlq_terminal", terminal);
        out.put("dlq_message_with_already_stored_uuid", dlqStoredUuid);
        out.put("pending_retained", pending); out.put("accepted_unreconciled", unresolved);
        out.put("stored_despite_unconfirmed_http", uncertainStored); out.put("integrity_mismatches", mismatches);
        out.put("retry_scheduled", retries); out.put("idempotent_replays", replays);
        out.put("http_duration_ms", stats(http)); out.put("send_to_response_ms", stats(response));
        out.put("send_to_commit_ms", stats(completed));
        out.put("resources", resources(dir.resolve("resources.tsv"), start, end));
        out.put("measurement_windows_10s", windows(events, start, duration, expected));
        out.put("recovery", recovery(meta, events)); out.put("issues", issues);
        out.put("loss_interpretation", "DLQ is terminal non-persistence, not disappearance. Retention is not pending if DB/DLQ already reconciled. Unreconciled acceptance requires investigation; no missing event is silently labeled loss.");
        return out;
    }

    static Map<String, Object> stats(List<Double> values) {
        Map<String, Object> m = new LinkedHashMap<>(); m.put("n", values.size());
        if (values.isEmpty()) return m;
        List<Double> s = values.stream().sorted().toList();
        double mean = s.stream().mapToDouble(Double::doubleValue).average().orElseThrow();
        m.put("mean", mean); m.put("median", s.size() % 2 == 0 ? (s.get(s.size()/2-1) + s.get(s.size()/2))/2 : s.get(s.size()/2));
        m.put("sd_sample", s.size() < 2 ? null : Math.sqrt(s.stream().mapToDouble(v -> (v-mean)*(v-mean)).sum()/(s.size()-1)));
        m.put("p95", s.get((int)Math.ceil(.95*s.size())-1)); m.put("p99", s.get((int)Math.ceil(.99*s.size())-1));
        m.put("max", s.getLast()); return m;
    }

    private static List<Map<String, Object>> windows(Map<String, Event> events, Instant start, int duration, int expected) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (int seconds=0; seconds<duration; seconds+=10) {
            Instant a=start.plusSeconds(seconds), b=start.plusSeconds(Math.min(seconds+10,duration));
            var measured=events.values().stream().filter(e->e.phase.equals("measure")).toList();
            long offered=measured.stream().filter(e->e.sent!=null && !e.sent.isBefore(a) && e.sent.isBefore(b)).count();
            long commit=measured.stream().filter(e->e.row!=null && e.commit!=null && !e.commit.isBefore(a) && e.commit.isBefore(b)).count();
            long pending=measured.stream().filter(e->e.status==expected && e.idMatches && e.response!=null && e.response.isBefore(b)
                && (e.commit==null || !e.commit.isBefore(b))).count();
            out.add(Map.of("start_seconds",seconds,"duration_seconds",Math.min(10,duration-seconds),
                "offered",offered,"unique_commits",commit,"accepted_not_persisted_at_boundary",pending));
        }
        return out;
    }

    static String hash(Event e, String dataset) throws IOException {
        var at = e.occurred.atOffset(ZoneOffset.UTC);
        String time = at.format(DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss", Locale.ROOT));
        if (at.getNano()/1000 != 0) time += String.format(Locale.ROOT, ".%06d", at.getNano()/1000);
        Map<String, Object> body = new TreeMap<>();
        body.put("actor_id", "k6-experiment"); body.put("entity_id", "E" + e.iteration);
        body.put("entity_type", "experiment"); body.put("event_id", e.id); body.put("event_type", "created");
        body.put("occurred_at", time + "Z"); body.put("payload", Map.of("value", e.iteration % 10));
        body.put("source", "experiment-" + dataset);
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(JSON.writeValueAsBytes(body))); }
        catch (java.security.NoSuchAlgorithmException x) { throw new IllegalStateException(x); }
    }

    private static boolean matches(Event e, String dataset) throws IOException {
        if (e.occurred == null) return false;
        JsonNode r = e.row;
        return r.path("event_type").asText().equals("created") && r.path("entity_type").asText().equals("experiment")
            && r.path("entity_id").asText().equals("E"+e.iteration) && r.path("actor_id").asText().equals("k6-experiment")
            && r.path("source").asText().equals("experiment-"+dataset) && e.occurred.equals(OffsetDateTime.parse(r.path("occurred_at").asText()).toInstant())
            && r.path("payload").size()==1 && r.path("payload").path("value").isIntegralNumber()
            && r.path("payload").path("value").asLong()==e.iteration%10 && r.path("content_hash").asText().equals(hash(e,dataset));
    }

    private static Map<String, Object> recovery(Properties meta, Map<String, Event> events) {
        Map<String, Object> out = new LinkedHashMap<>();
        String restored = meta.getProperty("fault_restore_utc");
        if (restored == null) { out.put("applicable", false); return out; }
        Instant at = Instant.parse(restored);
        out.put("applicable", true); out.put("restore_command_completed_utc", restored);
        List<Event> before = events.values().stream().filter(e -> e.phase.equals("measure") && e.sent != null
            && e.sent.isBefore(at) && (e.commit == null || e.commit.isAfter(at)) && e.status == 202 && e.idMatches).toList();
        out.put("accepted_not_persisted_at_restore", before.size());
        var first = events.values().stream().filter(e -> e.commit != null && e.commit.isAfter(at)).map(e -> e.commit).min(Instant::compareTo);
        out.put("first_commit_after_restore_ms", first.map(t -> Duration.between(at,t).toNanos()/1e6).orElse(null));
        boolean all = !before.isEmpty() && before.stream().allMatch(e -> e.row != null && e.commit != null);
        out.put("all_pre_restore_accepted_persisted", before.isEmpty() ? null : all);
        out.put("backlog_persistence_recovery_ms", all ? before.stream().map(e -> Duration.between(at,e.commit).toNanos()/1e6).max(Double::compare).orElseThrow() : null);
        out.put("stable_throughput_recovery", "not_estimated: first commit and complete backlog drainage are distinct; a rolling stability criterion requires the full campaign");
        return out;
    }

    private static Map<String, Object> resources(Path file, Instant start, Instant end) throws IOException {
        Map<String, List<Double>> cpu = new TreeMap<>(), memory = new TreeMap<>();
        if (Files.exists(file)) for (String line : Files.readAllLines(file)) {
            String[] p = line.split("\\t"); if (p.length != 4) continue;
            Instant at = Instant.parse(p[0]); if (at.isBefore(start) || !at.isBefore(end)) continue;
            cpu.computeIfAbsent(p[1], k -> new ArrayList<>()).add(Double.parseDouble(p[2].replace("%", "")));
            String usage = p[3].split(" / ")[0];
            double factor = usage.endsWith("GiB") ? 1024 : usage.endsWith("MiB") ? 1 : usage.endsWith("KiB") ? 1.0/1024 : 1.0/(1024*1024);
            memory.computeIfAbsent(p[1], k -> new ArrayList<>()).add(Double.parseDouble(usage.replaceAll("[^0-9.]", ""))*factor);
        }
        Map<String, Object> out = new TreeMap<>(); cpu.forEach((k,v) -> out.put(k, Map.of("cpu_percent",stats(v), "memory_mib",stats(memory.get(k)))));
        return out;
    }

    private static Double interval(Instant a, Instant b, String id, List<String> issues) {
        if (a == null || b == null) return null;
        double v = Duration.between(a,b).toNanos()/1e6;
        if (v < 0) { issues.add(id+":negative_interval"); return null; } return v;
    }
    private static String val(Double v) { return v == null ? "" : v.toString(); }
    private static BufferedReader reader(Path p) throws IOException { return new BufferedReader(new InputStreamReader(new GZIPInputStream(Files.newInputStream(p)), StandardCharsets.UTF_8)); }
    private static void readLines(Path p, java.util.function.Consumer<JsonNode> action) throws IOException {
        if (!Files.exists(p)) throw new IOException("missing evidence: " + p);
        try (var r = Files.newBufferedReader(p)) { String line; while ((line=r.readLine())!=null) {
            int brace = line.indexOf('{'); if (brace<0) continue; action.accept(JSON.readTree(line.substring(brace)));
        } }
    }
    static final class Event {
        final String id; String phase=""; long iteration; Instant occurred,sent,response,commit;
        int status,newCommits,replays,retries; boolean idMatches,dlqMarker; Double http; JsonNode row;
        Event(String id) { this.id=id; }
    }
}
