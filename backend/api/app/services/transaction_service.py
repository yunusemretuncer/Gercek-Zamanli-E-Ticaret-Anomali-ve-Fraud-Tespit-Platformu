import logging

from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.messaging.publisher import RabbitMQPublisher
from shared.models.transaction import Transaction
from shared.schemas.transaction import TransactionCreate, TransactionRead

logger = logging.getLogger(__name__)


class TransactionService:
    def __init__(self, db: Session, publisher: RabbitMQPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self._settings = get_settings()

    def create(self, payload: TransactionCreate) -> Transaction:
        tx = Transaction(
            user_id=payload.user_id,
            amount=payload.amount,
            timestamp=payload.timestamp,
            location=payload.location,
            is_fraud=False,  # worker will update this after rule eval
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)

        # Publish AFTER commit. We never emit events for rows that didn't
        # persist. The reverse risk (committed but failed to publish) is
        # logged; the worker (Step 3) should be idempotent on transaction id
        # so a replay job is safe.
        try:
            event = TransactionRead.model_validate(tx).model_dump(mode="json")
            self.publisher.publish(
                event,
                routing_key=self._settings.rabbitmq_transactions_routing_key,
            )
        except Exception:
            logger.exception(
                "Failed to publish transaction %s after commit", tx.id
            )

        return tx