package br.com.ilan.tcc.core;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.time.OffsetDateTime;
import java.util.UUID;

/** Distinguishes absent HTTP defaults from explicit nulls and prevents identity regeneration on replay. */
public final class AuditEventDeserializer extends JsonDeserializer<AuditEvent> {
    @Override
    public AuditEvent deserialize(JsonParser parser, DeserializationContext context) throws IOException {
        JsonNode wire = parser.readValueAsTree();
        if (wire == null || !wire.isObject()) throw JsonMappingException.from(parser, "event_must_be_object");
        try {
            UUID eventId = wire.has("event_id") ? UUID.fromString(text(wire, "event_id")) : null;
            OffsetDateTime occurredAt = wire.has("occurred_at")
                ? OffsetDateTime.parse(text(wire, "occurred_at")) : null;
            JsonNode payload = wire.has("payload") ? wire.get("payload") : null;
            if (payload != null && !payload.isObject()) throw new IllegalArgumentException("payload_must_be_object");
            return new AuditEvent(eventId, text(wire, "event_type"), text(wire, "entity_type"),
                text(wire, "entity_id"), text(wire, "actor_id"), text(wire, "source"), occurredAt, payload);
        } catch (IllegalArgumentException ex) {
            throw JsonMappingException.from(parser, "invalid_audit_event", ex);
        }
    }

    private static String text(JsonNode object, String field) {
        JsonNode value = object.get(field);
        if (value == null || !value.isTextual()) throw new IllegalArgumentException("invalid_" + field);
        return value.textValue();
    }
}
