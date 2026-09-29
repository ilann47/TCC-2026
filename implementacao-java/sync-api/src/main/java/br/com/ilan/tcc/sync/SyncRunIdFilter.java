package br.com.ilan.tcc.sync;

import br.com.ilan.tcc.core.RunContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Map;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class SyncRunIdFilter extends OncePerRequestFilter {
    private final ObjectMapper mapper;

    public SyncRunIdFilter(ObjectMapper mapper) { this.mapper = mapper; }

    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                               FilterChain chain) throws ServletException, IOException {
        try {
            RunContext.set(RunContext.validate(request.getHeader("X-Run-ID")), "sync");
        } catch (IllegalArgumentException ex) {
            response.setStatus(400);
            response.setContentType("application/json");
            mapper.writeValue(response.getOutputStream(), Map.of("detail", Map.of("reason", "invalid_run_id")));
            return;
        }
        try { chain.doFilter(request, response); }
        finally { RunContext.clear(); }
    }
}
