package br.com.ilan.tcc.consumer;

/** Reopen the Kafka session without confirming an unresolved source offset. */
public final class RetrySession extends RuntimeException {
    public RetrySession(String reason) { super(reason); }
    public RetrySession(String reason, Throwable cause) { super(reason, cause); }
}
