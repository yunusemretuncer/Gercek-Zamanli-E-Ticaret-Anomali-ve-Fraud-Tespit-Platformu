from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_publisher
from shared.config import get_settings
from shared.db.session import get_db
from shared.messaging.publisher import RabbitMQPublisher
from shared.schemas.transaction import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health(
    db: Session = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_publisher),
) -> HealthResponse:
    settings = get_settings()

    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    broker_status = "ok" if publisher.healthy() else "unavailable"

    overall = (
        "ok" if db_status == "ok" and broker_status == "ok" else "degraded"
    )

    return HealthResponse(
        status=overall,
        database=db_status,
        broker=broker_status,
        version=settings.app_version,
    )