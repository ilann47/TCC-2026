package br.com.ilan.tcc.experiment;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import static org.junit.jupiter.api.Assertions.*;

class ModelComparisonTest {
    @TempDir Path dir;
    Path rows(String name,int count,String inserted,boolean modified) throws Exception {
        StringBuilder lines=new StringBuilder();
        for(int i=0;i<count;i++) lines.append("{\"event_id\":\"").append(i).append("\",\"payload\":{\"value\":")
            .append(modified && i==0?9:i%10).append("},\"content_hash\":\"H").append(i)
            .append("\",\"persisted_at\":\"").append(inserted).append("\"}\n");
        Path p=dir.resolve(name);Files.writeString(p,lines);return p;
    }
    @Test void same50IgnoringOnlyInsertionTime() throws Exception {
        assertEquals(true,ModelComparison.compare(rows("a",50,"A",false),rows("b",50,"B",false)).get("same_ids_fields_payload_hash"));
    }
    @Test void alteredPayloadFails() throws Exception {
        assertEquals(false,ModelComparison.compare(rows("a",50,"A",false),rows("b",50,"B",true)).get("same_ids_fields_payload_hash"));
    }
    @Test void missingRecordFails() throws Exception {
        assertEquals(false,ModelComparison.compare(rows("a",50,"A",false),rows("b",49,"B",false)).get("same_ids_fields_payload_hash"));
    }
}
