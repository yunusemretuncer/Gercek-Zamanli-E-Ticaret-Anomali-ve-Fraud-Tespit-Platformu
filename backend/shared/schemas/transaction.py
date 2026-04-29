import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    amount: Decimal = Field(..., gt=0, max_digits=14, decimal_places=2)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    location: str = Field(..., min_length=1, max_length=128)


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: str
    amount: Decimal
    timestamp: datetime
    location: str
    is_fraud: bool
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str
    broker: str
    version: str