package br.com.ilan.tcc.experiment;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;

final class Instrumentation {
    private Instrumentation() {}
    static Map<String,Object> inspect(Path dir,Path output,Properties meta,Map<String,CampaignAnalyzer.Event> events,
            Instant start,int duration,int success,Map<String,Object> resources,List<String> issues) throws IOException {
        boolean enabled="1".equals(meta.getProperty("observer_enabled"));
        List<JsonNode> points=new ArrayList<>();
        if(enabled) {
            Path file=dir.resolve("observation.jsonl");
            if(!Files.exists(file))issues.add("observer_evidence_missing");
            else for(String line:Files.readAllLines(file)) if(!line.isBlank()) {
                JsonNode p=CampaignAnalyzer.JSON.readTree(line);
                if(!meta.getProperty("run_id").equals(p.path("run_id").asText()))issues.add("observer_run_mismatch");
                points.add(p);
            }
            if(!"0".equals(meta.getProperty("observer_exit")))issues.add("observer_exit_not_zero");
        }
        Instant end=start.plusSeconds(duration);
        List<JsonNode> measured=points.stream().filter(p->{Instant at=Instant.parse(p.path("sample_end").asText());return !at.isBefore(start)&&at.isBefore(end);}).toList();
        List<Double> gaps=new ArrayList<>();
        for(int i=1;i<measured.size();i++)gaps.add(Duration.between(Instant.parse(measured.get(i-1).path("sample_end").asText()),Instant.parse(measured.get(i).path("sample_end").asText())).toNanos()/1e6);
        if(enabled && !"model".equals(meta.getProperty("profile"))) {
            if(measured.size()<Math.ceil(duration/3.0))issues.add("observer_insufficient_coverage");
            if(gaps.stream().anyMatch(v->v<0||v>6000))issues.add("observer_clock_or_sampling_gap");
        }
        long dbErrors=measured.stream().filter(p->p.has("database_error")).count();
        long kafkaErrors=measured.stream().filter(p->p.has("kafka_error")).count();
        long clockErrors=measured.stream().filter(p->p.has("database_clock_utc") && (
            Instant.parse(p.path("database_clock_utc").asText()).isBefore(Instant.parse(p.path("sample_start").asText()).minusMillis(5)) ||
            Instant.parse(p.path("database_clock_utc").asText()).isAfter(Instant.parse(p.path("sample_end").asText()).plusMillis(5)))).count();
        if(clockErrors>0)issues.add("database_clock_outside_observer_round_trip");
        long maxLag=measured.stream().filter(p->p.has("kafka_group_lag")).mapToLong(p->p.path("kafka_group_lag").asLong()).max().orElse(0);
        if(measured.stream().anyMatch(p->p.has("kafka_group_lag")&&p.path("kafka_group_lag").asLong()<0))issues.add("negative_kafka_lag");
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("enabled",enabled);out.put("samples_in_measurement",measured.size());out.put("sample_gaps_ms",CampaignAnalyzer.stats(gaps));
        out.put("database_error_samples",dbErrors);out.put("kafka_error_samples",kafkaErrors);out.put("clock_error_samples",clockErrors);
        out.put("max_kafka_lag",meta.getProperty("variant").equals("async")?maxLag:null);
        List<Double> pendingSeries=new ArrayList<>();
        try(var writer=Files.newBufferedWriter(output.resolve("timeline.csv"))) {
            writer.write("seconds,accepted_http_cumulative,committed_accepted_cumulative,accepted_not_committed,kafka_lag,visible_measured_rows,observer_age_ms\n");
            for(int second=0;second<=duration;second++) {
                Instant at=start.plusSeconds(second);
                long accepted=0,committed=0;
                for(var e:events.values()) if(e.phase.equals("measure")&&e.status==success&&e.idMatches&&e.response!=null&&!e.response.isAfter(at)) {
                    accepted++;if(e.commit!=null&&!e.commit.isAfter(at)&&e.row!=null)committed++;
                }
                long pending=accepted-committed;pendingSeries.add((double)pending);
                JsonNode point=latest(points,at);
                writer.write(second+","+accepted+","+committed+","+pending+","+
                    (point!=null&&point.has("kafka_group_lag")?point.path("kafka_group_lag").asText():"")+","+
                    (point!=null&&point.has("database_measured")?point.path("database_measured").asText():"")+","+
                    (point==null?"":Duration.between(Instant.parse(point.path("sample_end").asText()),at).toMillis())+"\n");
            }
        }
        out.put("max_sampled_accepted_not_committed",pendingSeries.stream().mapToDouble(Double::doubleValue).max().orElse(0));
        var changes=new TreeMap<Instant,Integer>();
        for(var e:events.values())if(e.phase.equals("measure")&&e.status==success&&e.idMatches&&e.response!=null&&e.response.isBefore(end)
            &&(e.commit==null||e.commit.isAfter(e.response))) {
            changes.merge(e.response,1,Integer::sum);if(e.commit!=null&&e.commit.isBefore(end))changes.merge(e.commit,-1,Integer::sum);
        }
        int current=0,maximum=0;for(int change:changes.values()){current+=change;maximum=Math.max(maximum,current);}
        out.put("max_accepted_not_committed",maximum);
        out.put("pending_tail_slope_events_per_second",slope(pendingSeries.subList(pendingSeries.size()/2,pendingSeries.size())));
        out.put("generator",resource(resources,"tcc-e04-load-"+meta.getProperty("run_id"),2,2048));
        out.put("observer",resource(resources,"tcc-entrega04-observer-1",.25,256));
        if("1".equals(meta.getProperty("resources_enabled")) && !"model".equals(meta.getProperty("profile"))) {
            Map<?,?> gen=(Map<?,?>)out.get("generator");
            if(((Number)gen.get("samples")).intValue()<Math.ceil(duration/8.0))issues.add("generator_resources_insufficient_coverage");
            if(enabled && ((Number)((Map<?,?>)out.get("observer")).get("samples")).intValue()<Math.ceil(duration/8.0))issues.add("observer_resources_insufficient_coverage");
            if(Files.exists(dir.resolve("resources-errors.log")) && !Files.readString(dir.resolve("resources-errors.log")).isBlank())issues.add("resource_sampler_errors");
        }
        if(meta.containsKey("fault_restore_utc"))out.put("stable_recovery",stableRecovery(events,points,start,duration,Instant.parse(meta.getProperty("fault_restore_utc")),Integer.parseInt(meta.getProperty("rate")),success,meta.getProperty("variant").equals("async")));
        return out;
    }

    static Map<String,Object> stableRecovery(Map<String,CampaignAnalyzer.Event> events,List<JsonNode> points,Instant start,int duration,Instant restored,int rate,int success,boolean async) {
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("criterion","3 consecutive complete 10-second windows after restore, >=90% offered target committed/s, no HTTP errors, pending<=max(2,ceil(rate*0.1)), fresh healthy DB/lag observation; active input only");
        int consecutive=0;Instant candidate=null;
        for(int second=0;second+10<=duration;second+=10) {
            Instant a=start.plusSeconds(second),b=a.plusSeconds(10);
            if(a.isBefore(restored))continue;
            long committed=events.values().stream().filter(e->e.phase.equals("measure")&&e.row!=null&&e.commit!=null&&!e.commit.isBefore(a)&&e.commit.isBefore(b)).count();
            long errors=events.values().stream().filter(e->e.phase.equals("measure")&&e.response!=null&&!e.response.isBefore(a)&&e.response.isBefore(b)&&(e.status!=success||!e.idMatches)).count();
            long pending=events.values().stream().filter(e->e.phase.equals("measure")&&e.status==success&&e.idMatches&&e.response!=null&&!e.response.isAfter(b)&&(e.commit==null||e.commit.isAfter(b))).count();
            JsonNode p=latest(points,b);
            boolean healthy=p!=null && Duration.between(Instant.parse(p.path("sample_end").asText()),b).toMillis()<=3000 && !p.has("database_error") && p.has("database_measured")
                && (!async || (!p.has("kafka_error")&&p.has("kafka_group_lag")&&p.path("kafka_group_lag").asLong()<=Math.max(2,Math.ceil(rate*.1))));
            if(committed>=rate*9 && errors==0 && pending<=Math.max(2,Math.ceil(rate*.1)) && healthy) {
                if(consecutive++==0)candidate=a;
                if(consecutive==3) {
                    out.put("observed",true);out.put("start_after_restore_ms",Duration.between(restored,candidate).toNanos()/1e6);
                    out.put("confirmed_after_restore_ms",Duration.between(restored,b).toNanos()/1e6);
                    return out;
                }
            } else {consecutive=0;candidate=null;}
        }
        out.put("observed",false);out.put("reason","no qualifying 30-second active-input sequence observed; not automatically permanent failure");return out;
    }
    static double slope(List<Double> y) {
        if(y.size()<2)return 0;
        double xMean=(y.size()-1)/2.0,yMean=y.stream().mapToDouble(Double::doubleValue).average().orElse(0),num=0,den=0;
        for(int i=0;i<y.size();i++){num+=(i-xMean)*(y.get(i)-yMean);den+=(i-xMean)*(i-xMean);}return num/den;
    }
    @SuppressWarnings("unchecked")
    private static Map<String,Object> resource(Map<String,Object> all,String name,double cpus,double memoryMib) {
        Map<String,Object> out=new LinkedHashMap<>();out.put("name",name);out.put("samples",0);
        Object value=all.get(name);if(!(value instanceof Map<?,?>))return out;
        Map<String,Object> entry=(Map<String,Object>)value,cpu=(Map<String,Object>)entry.get("cpu_percent"),mem=(Map<String,Object>)entry.get("memory_mib");
        out.put("samples",cpu.get("n"));
        if(cpu.containsKey("p95"))out.put("cpu_p95_percent_of_limit",((Number)cpu.get("p95")).doubleValue()/cpus);
        if(mem.containsKey("max"))out.put("memory_max_percent_of_limit",100*((Number)mem.get("max")).doubleValue()/memoryMib);
        return out;
    }
    private static JsonNode latest(List<JsonNode> points,Instant at) {
        JsonNode latest=null;for(JsonNode p:points)if(!Instant.parse(p.path("sample_end").asText()).isAfter(at))latest=p;return latest;
    }
}
