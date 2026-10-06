package br.com.ilan.tcc.experiment;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import java.util.zip.GZIPOutputStream;
import static org.junit.jupiter.api.Assertions.*;

class CampaignAnalyzerTest {
    @TempDir Path dir;
    static final String RUN="12345678-1234-1234-1234-123456789abc";
    static final String DATA="abcdefab-1234-1234-1234-123456789abc";
    static final String ID="abcdefab-1234-1234-1234-000000000000";
    void fixture(int status, boolean persisted, boolean dlq, boolean retained) throws Exception {
        Files.writeString(dir.resolve("manifest.txt"), "run_id="+RUN+"\ndataset_id="+DATA+"\nvariant=async\nkind=validation\nprofile=steady\nrate=1\nmeasure_seconds=10\nmeasurement_start_ms=1791244800000\nk6_exit=0\n");
        var tags=new HashMap<String,String>(); tags.put("run_id",RUN); tags.put("variant","async");
        tags.put("phase","measure"); tags.put("event_id",ID); tags.put("iteration","0"); tags.put("occurred_at","2026-10-06T00:00:00Z");
        List<String> points=new ArrayList<>();
        points.add(point("experiment_sent","2026-10-06T00:00:00Z",1,tags));
        tags.put("http_status",Integer.toString(status)); tags.put("id_matches",Boolean.toString(status==202));
        points.add(point("experiment_response","2026-10-06T00:00:00.020Z",1,tags));
        points.add(point("http_req_duration","2026-10-06T00:00:00.020Z",19,tags));
        try(var gz=new GZIPOutputStream(Files.newOutputStream(dir.resolve("k6.jsonl.gz")))) { gz.write(String.join("\n",points).getBytes(java.nio.charset.StandardCharsets.UTF_8)); }
        var e=new CampaignAnalyzer.Event(ID); e.iteration=0; e.occurred=Instant.parse("2026-10-06T00:00:00Z");
        var row=new TreeMap<String,Object>(); row.put("event_id",ID); row.put("event_type","created"); row.put("entity_type","experiment");
        row.put("entity_id","E0"); row.put("actor_id","k6-experiment"); row.put("source","experiment-"+DATA);
        row.put("occurred_at","2026-10-06T00:00:00Z"); row.put("payload",Map.of("value",0)); row.put("content_hash",CampaignAnalyzer.hash(e,DATA));
        Files.writeString(dir.resolve("database.jsonl"),persisted?CampaignAnalyzer.JSON.writeValueAsString(row):"");
        var logs=new ArrayList<String>();
        if(persisted) logs.add(CampaignAnalyzer.JSON.writeValueAsString(Map.of("run_id",RUN,"event_id",ID,"milestone","commit_completed","timestamp","2026-10-06T00:00:00.030Z","status","persisted")));
        if(dlq) logs.add(CampaignAnalyzer.JSON.writeValueAsString(Map.of("run_id",RUN,"event_id",ID,"milestone","dlq_acknowledged")));
        Files.writeString(dir.resolve("app.log"),String.join("\n",logs));
        Files.writeString(dir.resolve("dlq.jsonl"),dlq?"{\"event_id\":\""+ID+"\"}":"");
        Files.writeString(dir.resolve("retained.jsonl"),retained?"{\"event_id\":\""+ID+"\"}":"");
        Files.writeString(dir.resolve("resources.tsv"),"");
    }
    String point(String metric,String time,double value,Map<String,String> tags) throws Exception {
        return CampaignAnalyzer.JSON.writeValueAsString(Map.of("type","Point","metric",metric,"data",Map.of("time",time,"value",value,"tags",tags)));
    }
    @Test void successKeepsHttpAndCommitDistinct() throws Exception {
        fixture(202,true,false,true); var s=CampaignAnalyzer.analyze(dir);
        assertEquals(true,s.get("instrument_valid")); assertEquals(1,s.get("accepted")); assertEquals(0,s.get("pending_retained"));
        assertEquals(20.0,((Map<?,?>)s.get("send_to_response_ms")).get("mean"));
        assertEquals(30.0,((Map<?,?>)s.get("send_to_commit_ms")).get("mean"));
    }
    @Test void expected503IsOutcomeNotInvalidInstrument() throws Exception {
        fixture(503,false,false,false); var s=CampaignAnalyzer.analyze(dir);
        assertEquals(true,s.get("instrument_valid")); assertEquals(1.0,s.get("http_error_fraction"));
    }
    @Test void dlqIsTerminalNotPendingOrLoss() throws Exception {
        fixture(202,false,true,true); var s=CampaignAnalyzer.analyze(dir);
        assertEquals(true,s.get("instrument_valid")); assertEquals(1,s.get("dlq_terminal")); assertEquals(0,s.get("pending_retained")); assertEquals(0,s.get("accepted_unreconciled"));
    }
    @Test void retainedWithoutCommitIsPending() throws Exception {
        fixture(202,false,false,true); var s=CampaignAnalyzer.analyze(dir);
        assertEquals(1,s.get("pending_retained")); assertEquals(0,s.get("accepted_unreconciled"));
    }
    @Test void conflictingAttemptDoesNotUnsaveOriginalUuid() throws Exception {
        fixture(202,true,true,true); var s=CampaignAnalyzer.analyze(dir);
        assertEquals(1,s.get("stored_at_observation_end")); assertEquals(0,s.get("dlq_terminal"));
        assertEquals(1,s.get("dlq_message_with_already_stored_uuid"));
    }
    @Test void missingAcceptedIsUnreconciledNotInventedLoss() throws Exception {
        fixture(202,false,false,false); assertEquals(1,CampaignAnalyzer.analyze(dir).get("accepted_unreconciled"));
    }
    @Test void missingCommitInvalidatesCollection() throws Exception {
        fixture(202,true,false,true); Files.writeString(dir.resolve("app.log"),"");
        assertEquals(false,CampaignAnalyzer.analyze(dir).get("instrument_valid"));
    }
    @Test void wrongHashInvalidatesCollection() throws Exception {
        fixture(202,true,false,true); var row=CampaignAnalyzer.JSON.readTree(Files.readString(dir.resolve("database.jsonl")));
        ((com.fasterxml.jackson.databind.node.ObjectNode)row).put("content_hash","bad"); Files.writeString(dir.resolve("database.jsonl"),row.toString());
        assertEquals(false,CampaignAnalyzer.analyze(dir).get("instrument_valid"));
    }
    @Test void nearestRankAndSampleDeviation() {
        var s=CampaignAnalyzer.stats(List.of(1.,2.,3.,4.)); assertEquals(2.5,s.get("median")); assertEquals(4.,s.get("p95")); assertEquals(4.,s.get("p99"));
    }
}
