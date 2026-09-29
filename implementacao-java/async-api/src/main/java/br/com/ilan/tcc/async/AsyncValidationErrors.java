package br.com.ilan.tcc.async;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class AsyncValidationErrors {
    @ExceptionHandler({HttpMessageNotReadableException.class, MethodArgumentNotValidException.class,
        IllegalArgumentException.class})
    public ResponseEntity<?> invalid() {
        return ResponseEntity.unprocessableEntity().body(Map.of("detail", Map.of("reason", "invalid_event")));
    }
}
