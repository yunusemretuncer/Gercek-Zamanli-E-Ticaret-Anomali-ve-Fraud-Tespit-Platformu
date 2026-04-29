import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, func
from shared.config import get_settings
from shared.db.session import get_db
from shared.models.transaction import Transaction
import redis as redis_lib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
mcp = FastMCP("fraud-detection")

redis_client = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)


def _get_db():
    return next(get_db())


@mcp.tool()
def get_recent_frauds(limit: int = 20) -> list[dict]:
    """
    Returns the most recent fraudulent transactions.
    
    Args:
        limit: Maximum number of fraud records to return (default 20)
    """
    db = _get_db()
    try:
        txs = db.execute(
            select(Transaction)
            .where(Transaction.is_fraud == True)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        ).scalars().all()

        return [
            {
                "transaction_id": str(tx.id),
                "user_id": tx.user_id,
                "amount": float(tx.amount),
                "location": tx.location,
                "timestamp": tx.timestamp.isoformat(),
                "created_at": tx.created_at.isoformat(),
            }
            for tx in txs
        ]
    finally:
        db.close()


@mcp.tool()
def check_user_status(user_id: str) -> dict:
    """
    Returns risk status and transaction summary for a specific user.
    
    Args:
        user_id: The user identifier to check
    """
    db = _get_db()
    try:
        # Toplam işlem sayısı
        total = db.execute(
            select(func.count()).where(Transaction.user_id == user_id)
        ).scalar() or 0

        # Fraud sayısı
        fraud_count = db.execute(
            select(func.count()).where(
                Transaction.user_id == user_id,
                Transaction.is_fraud == True
            )
        ).scalar() or 0

        # Son 24 saatteki işlem sayısı
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_count = db.execute(
            select(func.count()).where(
                Transaction.user_id == user_id,
                Transaction.timestamp >= since
            )
        ).scalar() or 0

        # Ortalama tutar
        avg_amount = db.execute(
            select(func.avg(Transaction.amount)).where(Transaction.user_id == user_id)
        ).scalar()

        # Redis'ten velocity bilgisi
        velocity_key = f"velocity:{user_id}"
        recent_velocity = redis_client.zcard(velocity_key) or 0

        # Risk seviyesi hesapla
        fraud_rate = (fraud_count / total * 100) if total > 0 else 0
        if fraud_rate >= 30 or recent_velocity > 5:
            risk = "HIGH"
        elif fraud_rate >= 10:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "user_id": user_id,
            "total_transactions": total,
            "fraud_count": fraud_count,
            "fraud_rate_pct": round(fraud_rate, 1),
            "recent_24h": recent_count,
            "recent_velocity": recent_velocity,
            "avg_amount": round(float(avg_amount), 2) if avg_amount else 0.0,
            "risk": risk,
        }
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting MCP server...")
    mcp.run(transport="stdio")
