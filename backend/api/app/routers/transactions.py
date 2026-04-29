from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.dependencies import get_publisher
from app.services.transaction_service import TransactionService
from shared.db.session import get_db
from shared.messaging.publisher import RabbitMQPublisher
from shared.models.transaction import Transaction
from shared.schemas.transaction import TransactionCreate, TransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new transaction",
)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_publisher),
) -> TransactionRead:
    service = TransactionService(db, publisher)
    tx = service.create(payload)
    return TransactionRead.model_validate(tx)


@router.get(
    "",
    response_model=list[TransactionRead],
    summary="List recent transactions",
)
def list_transactions(
    limit: int = 500,
    db: Session = Depends(get_db),
) -> list[TransactionRead]:
    txs = db.execute(
        select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
    ).scalars().all()
    return [TransactionRead.model_validate(tx) for tx in txs]


@router.get(
    "/users/{user_id}",
    response_model=list[TransactionRead],
    summary="Get transactions for a specific user",
)
def get_user_transactions(
    user_id: str,
    db: Session = Depends(get_db),
) -> list[TransactionRead]:
    txs = db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
    ).scalars().all()
    return [TransactionRead.model_validate(tx) for tx in txs]