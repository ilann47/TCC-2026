package br.com.ilan.tcc.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class CanonicalEventCodecTest {
    private static final UUID ID = UUID.fromString("123e4567-e89b-12d3-a456-426614174000");

    @Test
    void matchesThePythonGoldenFixtureIncludingUnicodeNestedKeysAndFractionalSeconds() throws Exception {
        JsonNode payload = CanonicalEventCodec.mapper().readTree("""
            {"z":1,"a":"ação","nested":{"b":2,"a":1},"n":1.0,"small":1e-5}
            """);
        AuditEvent event = new AuditEvent(ID, "created", "order", "E1", "A1", "web",
            OffsetDateTime.parse("2026-09-29T12:34:56.123Z"), payload);
        assertEquals("{" +
            "\"actor_id\":\"A1\",\"entity_id\":\"E1\",\"entity_type\":\"order\"," +
            "\"event_id\":\"123e4567-e89b-12d3-a456-426614174000\",\"event_type\":\"created\"," +
            "\"occurred_at\":\"2026-09-29T12:34:56.123000Z\"," +
            "\"payload\":{\"a\":\"ação\",\"n\":1.0,\"nested\":{\"a\":1,\"b\":2},\"small\":1e-05,\"z\":1}," +
            "\"source\":\"web\"}", CanonicalEventCodec.encode(event));
        assertEquals("b6d9e35494f7fe1eab1517ec1a73a3381077c9efcebe76bc9ac8b801d5972c59",
            CanonicalEventCodec.hash(event));
    }

    @Test
    void rejectsNonObjectPayloadAndEmptyRequiredFields() throws Exception {
        assertThrows(IllegalArgumentException.class, () -> new AuditEvent(ID, "", "order", "E1", "A1", "web",
            OffsetDateTime.parse("2026-09-29T12:34:56Z"), CanonicalEventCodec.mapper().readTree("{}")));
        assertThrows(IllegalArgumentException.class, () -> new AuditEvent(ID, "created", "order", "E1", "A1", "web",
            OffsetDateTime.parse("2026-09-29T12:34:56Z"), CanonicalEventCodec.mapper().readTree("[]")));
    }

    @Test
    void omittedIdentityGetsDefaultButExplicitNullOrIncompleteWireDoesNot() throws Exception {
        AuditEvent defaulted = CanonicalEventCodec.mapper().readValue("""
            {"event_type":"created","entity_type":"order","entity_id":"E1","actor_id":"A1","source":"web"}
            """, AuditEvent.class);
        org.junit.jupiter.api.Assertions.assertNotNull(defaulted.eventId());
        org.junit.jupiter.api.Assertions.assertNotNull(defaulted.occurredAt());
        assertThrows(com.fasterxml.jackson.databind.JsonMappingException.class, () ->
            CanonicalEventCodec.mapper().readValue("""
                {"event_id":null,"event_type":"created","entity_type":"order","entity_id":"E1","actor_id":"A1","source":"web"}
                """, AuditEvent.class));
    }

    @Test
    void matchesPythonFloatNotationAtThePlainDecimalBoundary() throws Exception {
        AuditEvent event = new AuditEvent(ID, "x", "x", "x", "x", "x",
            OffsetDateTime.parse("2026-09-29T12:34:56Z"),
            CanonicalEventCodec.mapper().readTree("{\"edge\":1e-4,\"whole\":1e5}"));
        assertEquals("ae79723184ea9922e4d41ec84b44b5416335dc7059faea431694efc5c18b132b",
            CanonicalEventCodec.hash(event));
    }
}
