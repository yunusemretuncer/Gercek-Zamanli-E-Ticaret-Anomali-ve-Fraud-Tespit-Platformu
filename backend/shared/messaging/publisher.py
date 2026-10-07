import json
import logging
import threading
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPError
from shared.messaging.topology import declare_topology

from shared.config import Settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """Thread-safe blocking RabbitMQ publisher with lazy reconnect.

    Pika's BlockingConnection is NOT thread-safe, so we serialize publishes
    with a lock. For higher throughput swap to aio-pika or one connection
    per worker process.

    Used by:
      - API service: publishes transaction.created events after commit
      - Worker service: publishes fraud.detected events after rule eval
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._params = pika.URLParameters(settings.rabbitmq_url)
        self._params.heartbeat = 30
        self._params.blocked_connection_timeout = 10
        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None
        self._lock = threading.Lock()#because Channel is not thread safe

    def connect(self) -> None:
        with self._lock:
            self._ensure_channel_locked()

    def _ensure_channel_locked(self) -> None:
        if self._channel is not None and self._channel.is_open:
            return
        if self._connection is None or self._connection.is_closed:
            logger.info(
                "Connecting to RabbitMQ at %s", self._settings.rabbitmq_host
            )
            self._connection = pika.BlockingConnection(self._params)
        self._channel = self._connection.channel()

        declare_topology(
            self._channel,
            self._settings,
        )

    def publish(self, payload: dict[str, Any], routing_key: str) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")

        with self._lock:
            for attempt in (1, 2):
                try:
                    self._ensure_channel_locked()
                    assert self._channel is not None
                    self._channel.basic_publish(
                        exchange=self._settings.rabbitmq_exchange,
                        routing_key=routing_key,
                        body=body,
                        properties=pika.BasicProperties(
                            content_type="application/json",
                            delivery_mode=pika.DeliveryMode.Persistent,
                        ),
                    )
                    return
                except (AMQPConnectionError, AMQPError, ConnectionError) as exc:
                    logger.warning(
                        "Publish failed (attempt %d): %s", attempt, exc
                    )
                    self._reset_locked()
                    if attempt == 2:
                        raise

    def healthy(self) -> bool:
        try:
            with self._lock:
                self._ensure_channel_locked()
            return True
        except Exception as exc:
            logger.warning("RabbitMQ health check failed: %s", exc)
            return False

    def close(self) -> None:
        with self._lock:
            self._reset_locked()

    def _reset_locked(self) -> None:
        try:
            if self._channel is not None and self._channel.is_open:
                self._channel.close()
        except Exception:
            pass
        try:
            if self._connection is not None and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass
        self._channel = None
        self._connection = None