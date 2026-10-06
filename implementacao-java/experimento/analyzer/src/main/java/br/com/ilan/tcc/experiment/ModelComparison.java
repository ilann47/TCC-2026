package br.com.ilan.tcc.experiment;
import java.nio.file.*;
import java.util.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/** Compares the same 50-record dataset, excluding only the insertion timestamp. */
public final class ModelComparison {
    private ModelComparison() {}
    public static void main(String[] args) throws Exception {
        if(args.length!=3) throw new IllegalArgumentException("model <sync export> <async export> <output JSON>");
        var out=compare(Path.of(args[0]),Path.of(args[1]));
        CampaignAnalyzer.JSON.writerWithDefaultPrettyPrinter().writeValue(Path.of(args[2]).toFile(),out);
        System.out.println(CampaignAnalyzer.JSON.writeValueAsString(out)); if(!Boolean.TRUE.equals(out.get("same_ids_fields_payload_hash")))System.exit(2);
    }
    static Map<String,Object> compare(Path sync,Path async) throws Exception {
        var a=read(sync); var b=read(async);
        return Map.of("kind","functional_model_equivalence_not_performance", "sync_records",a.size(),"async_records",b.size(),
            "same_ids_fields_payload_hash",a.size()==50 && b.size()==50 && a.equals(b),"excluded_field","persisted_at");
    }
    static Map<String,JsonNode> read(Path file) throws Exception {
        Map<String,JsonNode> rows=new TreeMap<>();
        for(String line:Files.readAllLines(file)) if(!line.isBlank()) {
            ObjectNode row=(ObjectNode)CampaignAnalyzer.JSON.readTree(line);row.remove("persisted_at");
            if(rows.put(row.path("event_id").asText(),row)!=null)throw new IllegalArgumentException("duplicate exported row");
        }
        return rows;
    }
}
