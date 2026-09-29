package br.com.ilan.tcc.sync;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import br.com.ilan.tcc.core.AuditEvent;
import br.com.ilan.tcc.storage.AuditRepository;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.transaction.CannotCreateTransactionException;

class SyncAuditControllerTest {
    @Test
    void unavailableDatabaseAtTransactionStartIsReportedAsUnknown503() {
        AuditRepository repository = Mockito.mock(AuditRepository.class);
        when(repository.persist(any())).thenThrow(new CannotCreateTransactionException("database unavailable"));
        var event = new AuditEvent(UUID.randomUUID(), "created", "order", "E1", "A1", "test",
            OffsetDateTime.parse("2026-09-29T12:34:56Z"), JsonNodeFactory.instance.objectNode());
        var response = new SyncAuditController(repository).create(event);
        assertEquals(503, response.getStatusCode().value());
        org.junit.jupiter.api.Assertions.assertTrue(response.getBody().toString().contains("unknown"));
    }
}
