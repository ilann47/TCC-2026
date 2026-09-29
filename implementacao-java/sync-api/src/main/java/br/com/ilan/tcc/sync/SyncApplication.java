package br.com.ilan.tcc.sync;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.info.Info;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@OpenAPIDefinition(info = @Info(title = "Auditoria - API sincrona", version = "0.1.0",
    description = "Persistencia REST: o retorno 201 confirma a transacao no PostgreSQL."))
@SpringBootApplication(scanBasePackages = "br.com.ilan.tcc")
public class SyncApplication {
    public static void main(String[] args) { SpringApplication.run(SyncApplication.class, args); }
}
