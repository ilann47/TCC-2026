package br.com.ilan.tcc.sync;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "br.com.ilan.tcc")
public class SyncApplication {
    public static void main(String[] args) { SpringApplication.run(SyncApplication.class, args); }
}
