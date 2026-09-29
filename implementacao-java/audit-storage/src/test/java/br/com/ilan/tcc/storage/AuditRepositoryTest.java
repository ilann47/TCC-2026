package br.com.ilan.tcc.storage;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.verify;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;

class AuditRepositoryTest {
    @Test
    void emptyAuditTableCanStillBeReady() {
        JdbcTemplate jdbc = Mockito.mock(JdbcTemplate.class);
        AuditRepository repository = new AuditRepository(jdbc, Mockito.mock(PlatformTransactionManager.class));
        assertTrue(repository.ready());
        verify(jdbc).execute("SELECT 1 FROM audit_records LIMIT 1");
    }
}
