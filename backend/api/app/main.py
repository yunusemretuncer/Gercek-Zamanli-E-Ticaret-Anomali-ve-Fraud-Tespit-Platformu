import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

import pika
from fastapi import FastAPI

from app.core.websocket_manager import manager
from app.routers import health, transactions, websocket
from shared.config import get_settings
from shared.db.session import Base, engine
from shared.messaging.publisher import RabbitMQPublisher
from shared.models import transaction  # noqa: F401


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def _fraud_consumer_thread(loop: asyncio.AbstractEventLoop):
    """
    Blocking pika consumer running in a background thread.
    Whenever a fraud.detected message arrives, it schedules
    a broadcast on the main asyncio event loop.
    """
    def on_fraud(ch, method, properties, body):
        try:
            alert = json.loads(body)
            logger.info("Fraud alert received: %s", alert)
            asyncio.run_coroutine_threadsafe(manager.broadcast(alert), loop)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            logger.exception("Failed to process fraud alert")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    # while for retry always that the worker dont dies
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
            channel = connection.channel()#tcp connection
            channel.basic_qos(prefetch_count=1)#one message at a time 
            channel.basic_consume(
                queue=settings.rabbitmq_fraud_alerts_queue,
                on_message_callback=on_fraud,
            )
            logger.info("Fraud consumer listening on: %s", settings.rabbitmq_fraud_alerts_queue)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            import time
            logger.warning("Fraud consumer: RabbitMQ not reachable (%s). Retrying in 5s...", e)
            time.sleep(5)
        except Exception:
            import time
            logger.exception("Fraud consumer crashed. Retrying in 5s...")
            time.sleep(5)

#Startup/shutdown of FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)#create tables if already doesnt exist

    publisher = RabbitMQPublisher(settings)
    #For API to live on
    try:
        publisher.connect()
        logger.info("RabbitMQ publisher connected")
    except Exception as exc:
        logger.warning("RabbitMQ not reachable at startup: %s", exc)

    app.state.publisher = publisher

    # Start fraud alert consumer in background thread
    loop = asyncio.get_event_loop()
    thread = threading.Thread(
        target=_fraud_consumer_thread,
        args=(loop,),
        daemon=True,
    )
    thread.start()
    logger.info("Fraud consumer thread started")

    try:
        yield
    finally:
        publisher.close()


app = FastAPI(
    title=f"{settings.app_name} - API",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)
app.include_router(transactions.router)
app.include_router(websocket.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.app_version}

