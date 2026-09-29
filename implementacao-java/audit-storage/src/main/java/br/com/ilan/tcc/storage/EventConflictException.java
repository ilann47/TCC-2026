package br.com.ilan.tcc.storage;

public final class EventConflictException extends RuntimeException {
    public EventConflictException() { super("event_id_content_conflict"); }
}
