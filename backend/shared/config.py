from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base settings shared by all backend services.

    Each service can subclass this to add service-specific fields,
    or use it directly. Reads from env vars and an optional .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    # App
    app_name: str = "Fraud Detection"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    postgres_user: str = "fraud"
    postgres_password: str = "fraud"
    postgres_db: str = "fraud_db"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # RabbitMQ
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672

    # Exchange + queues (event contract is shared by api/worker/mcp)
    rabbitmq_exchange: str = "fraud.events"
    rabbitmq_transactions_queue: str = "transactions_queue"
    rabbitmq_transactions_routing_key: str = "transaction.created"
    rabbitmq_fraud_alerts_queue: str = "fraud_alerts_queue"
    rabbitmq_fraud_alerts_routing_key: str = "fraud.detected"
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()