package br.com.ilan.tcc.core;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.UUID;

public record AuditAccepted(@JsonProperty("event_id") UUID eventId, String status) {
    public AuditAccepted(UUID eventId) { this(eventId, "accepted"); }
}
