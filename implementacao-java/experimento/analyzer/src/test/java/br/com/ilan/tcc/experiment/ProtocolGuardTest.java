package br.com.ilan.tcc.experiment;
import org.junit.jupiter.api.Test;
import java.util.Properties;
import static org.junit.jupiter.api.Assertions.*;
class ProtocolGuardTest {
    Properties run(){var p=new Properties();for(String k:new String[]{"instrument_source_sha256","analyzer_image_id","application_images_sha256"})p.setProperty(k,"HASH");p.setProperty("warmup_seconds","60");p.setProperty("measure_seconds","300");p.setProperty("drain_seconds","90");p.setProperty("observer_enabled","1");p.setProperty("resources_enabled","1");p.setProperty("telemetry","full");p.setProperty("profile","steady");p.setProperty("rate","25");p.setProperty("vus","128");return p;}
    com.fasterxml.jackson.databind.JsonNode frozen() throws Exception {return CampaignAnalyzer.JSON.readTree("{\"status\":\"ready_for_definitive_runs\",\"instrument_source_sha256\":\"HASH\",\"analyzer_image_id\":\"HASH\",\"application_images_sha256\":\"HASH\",\"warmup_seconds\":60,\"measure_seconds\":300,\"drain_seconds\":90,\"reference_rate\":100,\"normal_vus\":128,\"fault_vus\":332,\"fault_seconds\":40}");}
    @Test void matchingRunAllowed() throws Exception {assertDoesNotThrow(()->ProtocolGuard.validate(frozen(),run()));}
    @Test void imageDriftRefused() throws Exception {var p=run();p.setProperty("analyzer_image_id","DIFFERENT");assertThrows(IllegalArgumentException.class,()->ProtocolGuard.validate(frozen(),p));}
    @Test void changedDurationRefused() throws Exception {var p=run();p.setProperty("measure_seconds","30");assertThrows(IllegalArgumentException.class,()->ProtocolGuard.validate(frozen(),p));}
    @Test void unplannedRateRefused() throws Exception {var p=run();p.setProperty("rate","99");assertThrows(IllegalArgumentException.class,()->ProtocolGuard.validate(frozen(),p));}
    @Test void reducedTelemetryRefused() throws Exception {var p=run();p.setProperty("telemetry","control");assertThrows(IllegalArgumentException.class,()->ProtocolGuard.validate(frozen(),p));}
}
