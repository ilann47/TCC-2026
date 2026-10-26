package br.com.ilan.tcc.experiment;
import org.junit.jupiter.api.Test;
import com.fasterxml.jackson.databind.node.ObjectNode;
import static org.junit.jupiter.api.Assertions.*;

class CalibrationAssessmentTest {
    ObjectNode good() throws Exception {
        return (ObjectNode)CampaignAnalyzer.JSON.readTree("""
          {"kind":"calibration","profile":"steady","instrument_valid":true,"rate":10,"measure_seconds":20,"offered":200,"accepted":200,"stored_at_observation_end":200,"completed_per_second":9.95,
          "measurement_windows_10s":[{"unique_commits":99,"duration_seconds":10},{"unique_commits":100,"duration_seconds":10}],
          "instrumentation":{"enabled":true,"max_accepted_not_committed":1,"max_kafka_lag":2,"pending_tail_slope_events_per_second":0,"sample_gaps_ms":{"p95":1010},
          "generator":{"samples":10,"cpu_p95_percent_of_limit":30,"memory_max_percent_of_limit":25},"observer":{"samples":10,"cpu_p95_percent_of_limit":20,"memory_max_percent_of_limit":50}}}
          """);
    }
    @Test void boundedStableRunEligible() throws Exception {assertEquals(true,CalibrationAssessment.assess(good()).get("reference_eligible"));}
    @Test void droppedIterationsRejectReference() throws Exception {var s=good();s.put("dropped_iterations_all_phases",1);assertEquals(false,CalibrationAssessment.assess(s).get("reference_eligible"));}
    @Test void generatorSaturationIsNotTargetCapacity() throws Exception {var s=good();((ObjectNode)s.path("instrumentation").path("generator")).put("cpu_p95_percent_of_limit",95);assertTrue(CalibrationAssessment.assess(s).get("reasons").toString().contains("generator_cpu_headroom"));}
    @Test void growingQueueRejectsReference() throws Exception {var s=good();((ObjectNode)s.path("instrumentation")).put("pending_tail_slope_events_per_second",.1);assertEquals(false,CalibrationAssessment.assess(s).get("reference_eligible"));}
    @Test void normalHttpSuccessDoesNotHideIncompletePersistence() throws Exception {var s=good();s.put("stored_at_observation_end",199);assertEquals(false,CalibrationAssessment.assess(s).get("reference_eligible"));}
    @Test void missingWindowsAreNotZeroError() throws Exception {var s=good();s.remove("measurement_windows_10s");assertEquals(false,CalibrationAssessment.assess(s).get("reference_eligible"));}
    @Test void functionalModelCannotBecomeReference() throws Exception {var s=good();s.put("profile","model");assertEquals(false,CalibrationAssessment.assess(s).get("reference_eligible"));}
}
