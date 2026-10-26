package br.com.ilan.tcc.experiment;
import org.junit.jupiter.api.Test;
import java.time.Instant;
import java.util.*;
import com.fasterxml.jackson.databind.JsonNode;
import static org.junit.jupiter.api.Assertions.*;

class InstrumentationTest {
    static final Instant START=Instant.parse("2026-10-26T12:00:00Z");
    Map<String,CampaignAnalyzer.Event> events(int count) {
        Map<String,CampaignAnalyzer.Event> result=new LinkedHashMap<>();
        for(int i=0;i<count;i++) {
            var e=new CampaignAnalyzer.Event("E"+i);e.phase="measure";e.sent=START.plusSeconds(i).plusMillis(1);
            e.response=e.sent.plusMillis(10);e.commit=e.sent.plusMillis(20);e.status=202;e.idMatches=true;
            e.row=CampaignAnalyzer.JSON.createObjectNode();result.put(e.id,e);
        }return result;
    }
    List<JsonNode> points(int count,long lag) {
        List<JsonNode> result=new ArrayList<>();
        for(int i=0;i<=count;i++)result.add(CampaignAnalyzer.JSON.valueToTree(Map.of("sample_start",START.plusSeconds(i).toString(),"sample_end",START.plusSeconds(i).toString(),"database_measured",i,"kafka_group_lag",lag)));
        return result;
    }
    @Test void recoveryRequiresThreeCompleteActiveWindows() {
        var r=Instrumentation.stableRecovery(events(60),points(60,0),START,60,START.plusSeconds(5),1,202,true);
        assertEquals(true,r.get("observed"));assertEquals(5000.,r.get("start_after_restore_ms"));assertEquals(35000.,r.get("confirmed_after_restore_ms"));
    }
    @Test void lagPreventsFalseRecovery() {
        assertEquals(false,Instrumentation.stableRecovery(events(60),points(60,100),START,60,START,1,202,true).get("observed"));
    }
    @Test void idleDoesNotCountAsThroughputRecovery() {
        assertEquals(false,Instrumentation.stableRecovery(events(5),points(60,0),START,60,START.plusSeconds(5),1,202,true).get("observed"));
    }
    @Test void missingObservationIsNotHealthyZero() {
        assertEquals(false,Instrumentation.stableRecovery(events(60),List.of(),START,60,START,1,202,true).get("observed"));
    }
    @Test void shortWindowRemainsInconclusive() {
        assertEquals(false,Instrumentation.stableRecovery(events(20),points(20,0),START,20,START,1,202,true).get("observed"));
    }
    @Test void errorResetsConsecutiveWindows() {
        var e=events(60);e.get("E12").status=503;
        assertEquals(45000.,Instrumentation.stableRecovery(e,points(60,0),START,60,START.plusSeconds(5),1,202,true).get("confirmed_after_restore_ms"));
    }
    @Test void slopeDistinguishesQueueGrowth() {
        assertEquals(0.,Instrumentation.slope(List.of(2.,2.,2.,2.)),1e-9);
        assertEquals(1.,Instrumentation.slope(List.of(0.,1.,2.,3.)),1e-9);
    }
}
