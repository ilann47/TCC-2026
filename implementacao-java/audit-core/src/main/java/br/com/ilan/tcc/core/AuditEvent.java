package br.com.ilan.tcc.core;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;

/** The immutable wire contract shared by the REST and Kafka variants. */
@JsonDeserialize(using = AuditEventDeserializer.class)
public record AuditEvent(
    @JsonProperty("event_id") UUID eventId,
    @JsonProperty("event_type") String eventType,
    @JsonProperty("entity_type") String entityType,
    @JsonProperty("entity_id") String entityId,
    @JsonProperty("actor_id") String actorId,
    @JsonProperty("source") String source,
    @JsonProperty("occurred_at") OffsetDateTime occurredAt,
    @JsonProperty("payload") JsonNode payload
) {
    public AuditEvent {
        if (eventId == null) eventId = UUID.randomUUID();
        if (occurredAt == null) occurredAt = OffsetDateTime.now(ZoneOffset.UTC);
        if (payload == null) payload = JsonNodeFactory.instance.objectNode();
        if (!payload.isObject()) throw new IllegalArgumentException("payload_must_be_object");
        check(eventType, 100, "event_type");
        check(entityType, 100, "entity_type");
        check(entityId, 200, "entity_id");
        check(actorId, 200, "actor_id");
        check(source, 100, "source");
    }

    private static void check(String value, int maximum, String field) {
        if (value == null || value.isEmpty() || value.length() > maximum) {
            throw new IllegalArgumentException("invalid_" + field);
        }
    }
}
