package br.com.ilan.tcc.experiment;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class ControlAnalyzerTest {
    @TempDir Path dir;
    Properties fixture() throws Exception {
        String dataset="abcdefab-1234-1234-1234-123456789abc",id="abcdefab-1234-1234-1234-000000000000";
        Properties meta=new Properties();meta.setProperty("run_id",dataset);meta.setProperty("dataset_id",dataset);meta.setProperty("variant","sync");meta.setProperty("rate","1");meta.setProperty("measure_seconds","10");meta.setProperty("k6_exit","0");
        Files.writeString(dir.resolve("k6-summary.json"),"{\"metrics\":{\"experiment_sent{phase:measure}\":{\"values\":{\"count\":1}},\"experiment_success{phase:measure}\":{\"values\":{\"count\":1}}}}");
        var e=new CampaignAnalyzer.Event(id);e.iteration=0;e.occurred=Instant.parse("2026-10-06T00:00:00Z");
        Map<String,Object> row=new LinkedHashMap<>();row.put("event_id",id);row.put("event_type","created");row.put("entity_type","experiment");row.put("entity_id","E0");row.put("actor_id","k6-experiment");row.put("source","experiment-"+dataset);row.put("occurred_at",e.occurred.toString());row.put("payload",Map.of("value",0));row.put("content_hash",CampaignAnalyzer.hash(e,dataset));
        Files.writeString(dir.resolve("database.jsonl"),CampaignAnalyzer.JSON.writeValueAsString(row));return meta;
    }
    @Test void reconcilesOnlyAggregateClaims() throws Exception {var s=ControlAnalyzer.analyze(dir,fixture());assertEquals(true,s.get("instrument_valid"));assertFalse(s.containsKey("send_to_commit_ms"));}
    @Test void absentRowFailsControl() throws Exception {var p=fixture();Files.writeString(dir.resolve("database.jsonl"),"");assertEquals(false,ControlAnalyzer.analyze(dir,p).get("instrument_valid"));}
}
