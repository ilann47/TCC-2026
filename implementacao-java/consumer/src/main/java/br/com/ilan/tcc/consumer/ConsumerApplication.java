package br.com.ilan.tcc.consumer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "br.com.ilan.tcc")
public class ConsumerApplication {
    public static void main(String[] args) { SpringApplication.run(ConsumerApplication.class, args); }
}
