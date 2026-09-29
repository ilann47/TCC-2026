package br.com.ilan.tcc.async;

import java.util.Arrays;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/** Allows the single local Swagger UI to read and exercise the asynchronous API. */
@Configuration
public class AsyncSwaggerCorsConfig implements WebMvcConfigurer {
    private final String[] allowedOrigins;

    public AsyncSwaggerCorsConfig(@Value("${audit.swagger.allowed-origins}") String origins) {
        this.allowedOrigins = Arrays.stream(origins.split(","))
            .map(String::trim).filter(origin -> !origin.isEmpty()).toArray(String[]::new);
        if (allowedOrigins.length == 0) throw new IllegalArgumentException("swagger_allowed_origins_empty");
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        for (String path : List.of("/v3/api-docs", "/v3/api-docs/**", "/audit", "/health", "/live")) {
            registry.addMapping(path)
                .allowedOrigins(allowedOrigins)
                .allowedMethods("GET", "POST")
                .allowedHeaders("Content-Type", "X-Run-ID");
        }
    }
}
