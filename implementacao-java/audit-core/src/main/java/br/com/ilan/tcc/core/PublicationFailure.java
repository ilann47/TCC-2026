package br.com.ilan.tcc.core;

public final class PublicationFailure extends RuntimeException {
    private final String acceptance;
    private final String reason;

    public PublicationFailure(String acceptance, String reason, Throwable cause) {
        super(reason, cause);
        this.acceptance = acceptance;
        this.reason = reason;
    }

    public String acceptance() { return acceptance; }
    public String reason() { return reason; }
}
