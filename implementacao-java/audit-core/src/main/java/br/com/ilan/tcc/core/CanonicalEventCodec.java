package br.com.ilan.tcc.core;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.format.DateTimeFormatter;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

/** Mirrors Python json.dumps(..., ensure_ascii=False, separators=(",", ":"), sort_keys=True). */
public final class CanonicalEventCodec {
    private static final ObjectMapper MAPPER = new ObjectMapper().registerModule(new JavaTimeModule());
    private static final DateTimeFormatter SECONDS = DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss", Locale.ROOT);

    private CanonicalEventCodec() {}

    public static ObjectMapper mapper() { return MAPPER; }

    public static String encode(AuditEvent event) {
        Map<String, Object> fields = new TreeMap<>();
        fields.put("event_id", event.eventId().toString());
        fields.put("event_type", event.eventType());
        fields.put("entity_type", event.entityType());
        fields.put("entity_id", event.entityId());
        fields.put("actor_id", event.actorId());
        fields.put("source", event.source());
        fields.put("occurred_at", formatTime(event));
        fields.put("payload", event.payload());
        StringBuilder out = new StringBuilder();
        write(fields, out);
        return out.toString();
    }

    public static String hash(AuditEvent event) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                .digest(encode(event).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    private static String formatTime(AuditEvent event) {
        var value = event.occurredAt();
        int microseconds = value.getNano() / 1_000;
        String suffix = value.getOffset().getTotalSeconds() == 0 ? "Z" : value.getOffset().toString();
        return value.format(SECONDS) + (microseconds == 0 ? "" : String.format(Locale.ROOT, ".%06d", microseconds)) + suffix;
    }

    private static void write(Object value, StringBuilder out) {
        if (value instanceof Map<?, ?> map) {
            out.append('{');
            boolean first = true;
            for (var entry : map.entrySet()) {
                if (!first) out.append(',');
                writeString((String) entry.getKey(), out);
                out.append(':');
                write(entry.getValue(), out);
                first = false;
            }
            out.append('}');
        } else if (value instanceof JsonNode node) {
            writeNode(node, out);
        } else if (value instanceof String string) {
            writeString(string, out);
        } else if (value == null) {
            out.append("null");
        } else {
            throw new IllegalArgumentException("unsupported_canonical_value");
        }
    }

    private static void writeNode(JsonNode node, StringBuilder out) {
        if (node.isObject()) {
            Map<String, Object> sorted = new TreeMap<>();
            Iterator<Map.Entry<String, JsonNode>> entries = node.fields();
            entries.forEachRemaining(entry -> sorted.put(entry.getKey(), entry.getValue()));
            write(sorted, out);
        } else if (node.isArray()) {
            out.append('[');
            for (int i = 0; i < node.size(); i++) {
                if (i > 0) out.append(',');
                writeNode(node.get(i), out);
            }
            out.append(']');
        } else if (node.isTextual()) {
            writeString(node.textValue(), out);
        } else if (node.isNumber()) {
            out.append(number(node));
        } else if (node.isBoolean()) {
            out.append(node.booleanValue());
        } else if (node.isNull()) {
            out.append("null");
        } else {
            throw new IllegalArgumentException("unsupported_payload_value");
        }
    }

    private static String number(JsonNode node) {
        if (!node.isFloatingPointNumber()) return node.asText();
        double value = node.doubleValue();
        if (!Double.isFinite(value)) throw new IllegalArgumentException("non_finite_number");
        String raw = Double.toString(value);
        int exponentAt = raw.indexOf('E');
        if (exponentAt < 0) return raw;
        int exponent = Integer.parseInt(raw.substring(exponentAt + 1));
        if (exponent >= -4 && exponent < 16) {
            String plain = java.math.BigDecimal.valueOf(value).stripTrailingZeros().toPlainString();
            return plain.contains(".") ? plain : plain + ".0";
        }
        String significand = raw.substring(0, exponentAt).replaceFirst("\\.0$", "");
        return significand + "e" + (exponent >= 0 ? "+" : "-")
            + String.format(Locale.ROOT, "%02d", Math.abs(exponent));
    }

    private static void writeString(String value, StringBuilder out) {
        try {
            out.append(MAPPER.writeValueAsString(value));
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("invalid_json_string", ex);
        }
    }
}
