package br.com.ilan.tcc.experiment;
import com.fasterxml.jackson.databind.JsonNode;
import java.nio.file.*;
import java.time.*;
import java.util.*;

/** Reduced-telemetry control: aggregate HTTP + independently verified DB; no per-event latency claims. */
final class ControlAnalyzer {
    static Map<String,Object> analyze(Path dir,Properties meta) throws java.io.IOException {
        JsonNode k6=CampaignAnalyzer.JSON.readTree(Files.readString(dir.resolve("k6-summary.json"))).path("metrics");
        int sent=k6.path("experiment_sent{phase:measure}").path("values").path("count").asInt(-1);
        int accepted=k6.path("experiment_success{phase:measure}").path("values").path("count").asInt(-1);
        List<String> issues=new ArrayList<>();int stored=0,integrity=0;
        Set<String> ids=new HashSet<>();
        for(String line:Files.readAllLines(dir.resolve("database.jsonl")))if(!line.isBlank()) {
            JsonNode row=CampaignAnalyzer.JSON.readTree(line);
            long i=Long.parseLong(row.path("entity_id").asText().substring(1));
            var e=new CampaignAnalyzer.Event(row.path("event_id").asText());e.row=row;e.iteration=i;
            e.occurred=Instant.parse("2026-10-06T00:00:00Z").plusMillis(i);
            if(!CampaignAnalyzer.matches(e,meta.getProperty("dataset_id")))issues.add("database_content_mismatch");
            if(i<1_000_000_000) {stored++;if(CampaignAnalyzer.matches(e,meta.getProperty("dataset_id")))integrity++;}
            if(!ids.add(e.id))issues.add("duplicate_database_row");
        }
        if(sent<1||accepted!=sent||stored!=sent)issues.add("control_aggregate_counts_not_reconciled");
        if(!"0".equals(meta.getProperty("k6_exit")))issues.add("k6_exit_not_zero");
        Map<String,Object> out=new LinkedHashMap<>();out.put("kind","calibration_reduced_telemetry_control_not_definitive");
        out.put("run_id",meta.getProperty("run_id"));out.put("variant",meta.getProperty("variant"));out.put("rate",Integer.parseInt(meta.getProperty("rate")));
        out.put("measure_seconds",Integer.parseInt(meta.getProperty("measure_seconds")));out.put("offered",sent);out.put("accepted",accepted);
        out.put("stored_at_observation_end",stored);out.put("database_content_matches",integrity);
        out.put("dropped_iterations_all_phases",k6.path("dropped_iterations").path("values").path("count").asInt());
        out.put("http_duration_ms",k6.path("http_req_duration{phase:measure}").path("values"));out.put("instrument_valid",issues.isEmpty());out.put("issues",issues);
        out.put("limitation","No detailed client event stream, live observer or resource sampler. Aggregate HTTP and deterministic DB comparison only. Not definitive evidence or per-event end-to-end latency.");return out;
    }
}
