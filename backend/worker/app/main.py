import json
import logging
import sys
import time
from decimal import Decimal

import pika

from shared.config import get_settings
from shared.db.session import get_db
from shared.models.transaction import Transaction
from shared.messaging.publisher import RabbitMQPublisher
from app.rules import velocity, amount, location

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


def evaluate_fraud(event: dict) -> tuple[bool, list[str]]:
    """
    3 kuralı değerlendirir. En az 2 ihlal → fraud.
    Döner: (is_fraud, violated_rules)
    """
    tx_id    = event["id"]
    user_id  = event["user_id"]
    amt      = Decimal(event["amount"])
    loc      = event["location"]
    from datetime import datetime, timezone
    ts = datetime.fromisoformat(event["timestamp"]).timestamp()

    violated = []

    if velocity.check(user_id, tx_id, ts):
        violated.append("velocity")
        logger.info("  [velocity] VIOLATED for user %s", user_id)

    if amount.check(user_id, tx_id, amt, ts):
        violated.append("amount")
        logger.info("  [amount] VIOLATED for user %s", user_id)

    if location.check(user_id, loc, ts):
        violated.append("location")
        logger.info("  [location] VIOLATED for user %s", user_id)

    is_fraud = len(violated) >= 2
    return is_fraud, violated


def process_transaction(ch, method, properties, body, publisher):
    try:
        event = json.loads(body)
        tx_id   = event.get("id")
        user_id = event.get("user_id")
        amount_val = event.get("amount")
        logger.info("Received transaction id=%s user=%s amount=%s", tx_id, user_id, amount_val)

        is_fraud, violated = evaluate_fraud(event)

        # Postgres güncelle
        db = next(get_db())
        try:
            tx = db.get(Transaction, tx_id)
            if tx is None:
                logger.warning("Transaction %s not found in DB — skipping", tx_id)
            else:
                tx.is_fraud = is_fraud
                db.commit()
                logger.info("Marked transaction %s is_fraud=%s violated=%s", tx_id, is_fraud, violated)
        finally:
            db.close()

        # Fraud ise alert publish et
        if is_fraud:
            from datetime import datetime, timezone
            alert = {
                "transaction_id": tx_id,
                "user_id": user_id,
                "rules_violated": violated,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                publisher.publish(
                    alert,
                    routing_key=settings.rabbitmq_fraud_alerts_routing_key,
                )
                logger.info("Published fraud.detected for transaction %s", tx_id)
            except Exception:
                logger.exception("Failed to publish fraud alert for %s", tx_id)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        logger.exception("Failed to process transaction — sending nack")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    logger.info("Worker starting up...")
    publisher = RabbitMQPublisher(settings)

    while True:
        try:
            credentials = pika.PlainCredentials(
                settings.rabbitmq_user, settings.rabbitmq_password
            )
            params = pika.ConnectionParameters(
                host=settings.rabbitmq_host,
                port=settings.rabbitmq_port,
                credentials=credentials,
                heartbeat=60,
            )
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=settings.rabbitmq_transactions_queue,
                on_message_callback=lambda ch, method, props, body: process_transaction(
                    ch, method, props, body, publisher
                ),
            )

            logger.info("Listening on queue: %s", settings.rabbitmq_transactions_queue)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.warning("RabbitMQ not reachable (%s). Retrying in 5s...", e)
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Worker shutting down.")
            sys.exit(0)


if __name__ == "__main__":
    main()
