from pika.adapters.blocking_connection import BlockingChannel

from shared.config import Settings


def declare_topology(
    channel: BlockingChannel,
    settings: Settings,
) -> None:
    channel.exchange_declare(
        exchange=settings.rabbitmq_exchange,
        exchange_type="topic",
        durable=True,
    )

    channel.queue_declare(
        queue=settings.rabbitmq_transactions_queue,
        durable=True,
    )

    channel.queue_bind(
        queue=settings.rabbitmq_transactions_queue,
        exchange=settings.rabbitmq_exchange,
        routing_key=settings.rabbitmq_transactions_routing_key,
    )

    channel.queue_declare(
        queue=settings.rabbitmq_fraud_alerts_queue,
        durable=True,
    )

    channel.queue_bind(
        queue=settings.rabbitmq_fraud_alerts_queue,
        exchange=settings.rabbitmq_exchange,
        routing_key=settings.rabbitmq_fraud_alerts_routing_key,
    )