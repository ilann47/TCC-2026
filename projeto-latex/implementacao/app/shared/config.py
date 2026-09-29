import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://audit@localhost:5432/auditdb"
)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "audit-events")
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", "audit-events-dlq")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "audit-persistence")
DELIVERY_TIMEOUT_SECONDS = float(os.getenv("DELIVERY_TIMEOUT_SECONDS", "10"))
DB_TIMEOUT_SECONDS = int(os.getenv("DB_TIMEOUT_SECONDS", "5"))
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_BACKOFF_SECONDS = float(os.getenv("RETRY_BACKOFF_SECONDS", "0.5"))
RETRY_BACKOFF_MAX_SECONDS = float(os.getenv("RETRY_BACKOFF_MAX_SECONDS", "5"))
RECONNECT_SECONDS = float(os.getenv("RECONNECT_SECONDS", "2"))

if min(DELIVERY_TIMEOUT_SECONDS, DB_TIMEOUT_SECONDS, RETRY_ATTEMPTS,
       RETRY_BACKOFF_SECONDS, RETRY_BACKOFF_MAX_SECONDS, RECONNECT_SECONDS) <= 0:
    raise ValueError("Timeouts and retry parameters must be positive")
if RETRY_ATTEMPTS > 10 or DB_TIMEOUT_SECONDS > 30 or DELIVERY_TIMEOUT_SECONDS > 30 or RETRY_BACKOFF_MAX_SECONDS > 5:
    raise ValueError("Retry budget must remain below consumer max.poll.interval.ms")
if RETRY_ATTEMPTS * (4 * DB_TIMEOUT_SECONDS + RETRY_BACKOFF_MAX_SECONDS) + DELIVERY_TIMEOUT_SECONDS >= 500:
    raise ValueError("Configured processing budget exceeds the 500-second safety margin")
