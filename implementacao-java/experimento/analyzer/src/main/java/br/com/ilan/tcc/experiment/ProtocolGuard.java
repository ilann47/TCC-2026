package br.com.ilan.tcc.experiment;
import com.fasterxml.jackson.databind.JsonNode;
import java.nio.file.*;
import java.util.*;

/** Refuses parameter drift before a definitive run touches the experimental state. */
final class ProtocolGuard {
    static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("protocol <frozen JSON> <new run manifest>");
        Properties actual=new Properties();try(var reader=Files.newBufferedReader(Path.of(args[1]))){actual.load(reader);}
        validate(CampaignAnalyzer.JSON.readTree(Files.readString(Path.of(args[0]))),actual);
        System.out.println("Frozen protocol and image/source hashes match this run.");
    }
    static void validate(JsonNode frozen,Properties actual) {
        if(!"ready_for_definitive_runs".equals(frozen.path("status").asText()))throw new IllegalArgumentException("protocol not ready");
        for(String name:List.of("instrument_source_sha256","analyzer_image_id","application_images_sha256"))
            if(!frozen.path(name).asText().equals(actual.getProperty(name)))throw new IllegalArgumentException("frozen mismatch: "+name);
        for(String name:List.of("warmup_seconds","measure_seconds","drain_seconds"))
            if(frozen.path(name).asInt()!=Integer.parseInt(actual.getProperty(name)))throw new IllegalArgumentException("frozen mismatch: "+name);
        if(!"1".equals(actual.getProperty("observer_enabled"))||!"1".equals(actual.getProperty("resources_enabled"))||!"full".equals(actual.getProperty("telemetry")))throw new IllegalArgumentException("full instrumentation required");
        int reference=frozen.path("reference_rate").asInt(),rate=Integer.parseInt(actual.getProperty("rate"));String profile=actual.getProperty("profile");
        boolean fault=Set.of("postgres-stop","consumer-stop").contains(profile);
        boolean allowed="steady".equals(profile)?Set.of(reference/4,reference/2,reference*3/4,reference).contains(rate):
            "burst".equals(profile)?rate==reference:fault&&rate==reference/4;
        if(!allowed)throw new IllegalArgumentException("rate/profile outside frozen matrix");
        int expectedVus=frozen.path(fault?"fault_vus":"normal_vus").asInt();
        if(expectedVus!=Integer.parseInt(actual.getProperty("vus")))throw new IllegalArgumentException("frozen VU count mismatch");
        if(fault&&frozen.path("fault_seconds").asInt()!=Integer.parseInt(actual.getProperty("fault_seconds_requested")))throw new IllegalArgumentException("frozen fault duration mismatch");
    }
}
