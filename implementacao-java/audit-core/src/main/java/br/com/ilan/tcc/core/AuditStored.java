package br.com.ilan.tcc.core;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.OffsetDateTime;
import java.util.UUID;

public record AuditStored(
    @JsonProperty("event_id") UUID eventId,
    String status,
    @JsonProperty("content_hash") String contentHash,
    @JsonProperty("persisted_at") OffsetDateTime persistedAt
) {}
