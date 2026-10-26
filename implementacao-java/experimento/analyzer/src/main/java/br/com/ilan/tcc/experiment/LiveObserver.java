package br.com.ilan.tcc.experiment;

import java.nio.file.*;
import java.sql.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.common.TopicPartition;

/** Read-only observer. Samples DB visibility and Kafka offsets, not physical commit instants. */
public final class LiveObserver {
    private LiveObserver() {}
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("observe <output directory>");
        Path out = Path.of(args[0]);
        String run = env("RUN_ID"), dataset = env("DATASET_ID"), variant = env("VARIANT");
        String databaseHost=env("OBSERVER_POSTGRES_HOST");
        if(!databaseHost.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}"))throw new IllegalArgumentException("observer requires the captured experimental PostgreSQL IPv4 address");
        UUID.fromString(run); UUID.fromString(dataset);
        if (!Set.of("sync","async").contains(variant)) throw new IllegalArgumentException("variant");
        String topic = "audit-"+run;
        var main = new TopicPartition(topic,0);
        var dlq = new TopicPartition(topic+"-dlq",0);
        Properties props = new Properties();
        props.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG,"kafka:9092");
        props.put(AdminClientConfig.DEFAULT_API_TIMEOUT_MS_CONFIG,"1500");
        props.put(AdminClientConfig.REQUEST_TIMEOUT_MS_CONFIG,"1000");
        props.put(AdminClientConfig.CLIENT_ID_CONFIG,"observer-"+run);
        Connection db = null;
        try (Admin admin = Admin.create(props);
             var writer = Files.newBufferedWriter(out.resolve("observation.jsonl"), StandardOpenOption.CREATE_NEW)) {
            while (!Files.exists(out.resolve(".stop-observer"))) {
                long mono = System.nanoTime();
                Map<String,Object> point = new LinkedHashMap<>();
                point.put("sample_start",Instant.now().toString()); point.put("run_id",run);
                point.put("variant",variant);
                try {
                    if (db == null || db.isClosed()) {
                        db = DriverManager.getConnection("jdbc:postgresql://"+databaseHost+":5432/auditdb?connectTimeout=1&socketTimeout=1&loginTimeout=2", "audit", env("POSTGRES_PASSWORD"));
                        db.setReadOnly(true); db.setAutoCommit(true);
                    }
                    try (var sql = db.prepareStatement("SELECT count(*), count(*) FILTER (WHERE substring(entity_id from 2)::bigint < 1000000000), clock_timestamp() FROM audit_records WHERE source=?")) {
                        sql.setQueryTimeout(1); sql.setString(1,"experiment-"+dataset);
                        try (var result = sql.executeQuery()) {
                            result.next(); point.put("database_total",result.getLong(1));
                            point.put("database_measured",result.getLong(2));
                            point.put("database_clock_utc",result.getObject(3,OffsetDateTime.class).toInstant().toString());
                        }
                    }
                } catch (SQLException e) {
                    point.put("database_error",e.getSQLState()==null?e.getClass().getSimpleName():e.getSQLState());
                    if (db!=null) try { db.close(); } catch(SQLException ignored) { }
                    db=null;
                }
                if (variant.equals("async")) {
                    try {
                        var committed = admin.listConsumerGroupOffsets(topic+"-group").partitionsToOffsetAndMetadata().get(2,TimeUnit.SECONDS).get(main);
                        var offsets = admin.listOffsets(Map.of(main,OffsetSpec.latest(),dlq,OffsetSpec.latest())).all().get(2,TimeUnit.SECONDS);
                        point.put("kafka_end_offset",offsets.get(main).offset());
                        point.put("dlq_end_offset",offsets.get(dlq).offset());
                        point.put("consumer_offset_established",committed!=null);
                        point.put("consumer_committed_offset",committed==null?0:committed.offset());
                        point.put("kafka_group_lag",offsets.get(main).offset()-(committed==null?0:committed.offset()));
                    } catch (Exception e) { point.put("kafka_error",e.getClass().getSimpleName()); }
                }
                point.put("sample_end",Instant.now().toString());
                point.put("duration_ms",(System.nanoTime()-mono)/1e6);
                writer.write(CampaignAnalyzer.JSON.writeValueAsString(point)); writer.newLine(); writer.flush();
                long remaining=1_000_000_000L-(System.nanoTime()-mono);
                if (remaining>0) TimeUnit.NANOSECONDS.sleep(remaining);
            }
        } finally { if(db!=null) try{db.close();}catch(SQLException ignored){} }
    }
    private static String env(String name) {
        String value=System.getenv(name);
        if(value==null || value.isBlank())throw new IllegalArgumentException("missing environment variable "+name);
        return value;
    }
}
