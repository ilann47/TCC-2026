package br.com.ilan.tcc.experiment;
import com.fasterxml.jackson.databind.JsonNode;
import java.nio.file.*;
import java.util.*;

public final class CalibrationAssessment {
    private CalibrationAssessment() {}
    public static void main(String[] args) throws Exception {
        if(args.length!=1)throw new IllegalArgumentException("assess <summary.json>");
        Path file=Path.of(args[0]);JsonNode s=CampaignAnalyzer.JSON.readTree(Files.readString(file));
        var out=assess(s);Path dest=file.resolveSibling("calibration-assessment.json");
        if(Files.exists(dest))throw new IllegalArgumentException("existing assessment");
        CampaignAnalyzer.JSON.writerWithDefaultPrettyPrinter().writeValue(dest.toFile(),out);
        System.out.println(CampaignAnalyzer.JSON.writeValueAsString(out));
    }
    static Map<String,Object> assess(JsonNode s) {
        List<String> reasons=new ArrayList<>();double rate=s.path("rate").asDouble(),seconds=s.path("measure_seconds").asDouble(),offered=s.path("offered").asDouble();
        if(!"steady".equals(s.path("profile").asText())||!"calibration".equals(s.path("kind").asText()))reasons.add("not_a_steady_calibration_run");
        if(!s.path("instrument_valid").asBoolean())reasons.add("instrument_invalid");
        if(rate<=0||seconds<6||Math.abs(offered/(rate*seconds)-1)>.02)reasons.add("offered_rate_outside_2pct");
        if(s.path("accepted").asInt()!=s.path("offered").asInt()||s.path("stored_at_observation_end").asInt()!=s.path("offered").asInt())reasons.add("not_all_offered_accepted_and_stored");
        if(s.path("dropped_iterations_all_phases").asDouble()!=0)reasons.add("dropped_iterations");
        for(String key:List.of("dlq_terminal","pending_retained","accepted_unreconciled","integrity_mismatches"))if(s.path(key).asDouble()!=0)reasons.add(key);
        if(!s.has("completed_per_second")||s.path("completed_per_second").asDouble()<rate*.95)reasons.add("completed_rate_below_95pct");
        if(s.path("measurement_windows_10s").size()!=Math.ceil(seconds/10))reasons.add("missing_throughput_windows");
        for(JsonNode w:s.path("measurement_windows_10s"))if(w.path("unique_commits").asDouble()<rate*w.path("duration_seconds").asDouble()*.9)reasons.add("10s_window_below_90pct");
        JsonNode i=s.path("instrumentation");if(!i.path("enabled").asBoolean())reasons.add("observer_disabled");
        for(String key:List.of("database_error_samples","kafka_error_samples","clock_error_samples"))if(i.path(key).asLong()!=0)reasons.add(key);
        if(i.path("pending_tail_slope_events_per_second").asDouble()>.01)reasons.add("queue_growing");
        double limit=Math.max(5,Math.ceil(rate*.25));
        if(i.path("max_accepted_not_committed").asDouble()>limit||i.path("max_kafka_lag").asDouble()>limit)reasons.add("backlog_above_reference_limit");
        check(i.path("generator"),"generator",70,75,reasons);check(i.path("observer"),"observer",80,85,reasons);
        if(i.path("sample_gaps_ms").path("p95").asDouble(Double.POSITIVE_INFINITY)>2500)reasons.add("observer_cadence_too_slow");
        Map<String,Object> out=new LinkedHashMap<>();out.put("run_id",s.path("run_id").asText());out.put("variant",s.path("variant").asText());out.put("rate",rate);
        out.put("reference_eligible",reasons.isEmpty());out.put("reasons",reasons.stream().distinct().toList());return out;
    }
    private static void check(JsonNode point,String name,double cpu,double memory,List<String> reasons) {
        if(point.path("samples").asInt()==0)reasons.add(name+"_missing_resources");
        if(point.path("cpu_p95_percent_of_limit").asDouble(Double.POSITIVE_INFINITY)>cpu)reasons.add(name+"_cpu_headroom");
        if(point.path("memory_max_percent_of_limit").asDouble(Double.POSITIVE_INFINITY)>memory)reasons.add(name+"_memory_headroom");
    }
}
