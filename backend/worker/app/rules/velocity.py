"""
Velocity Rule
─────────────
Aynı user_id için son 60 saniyede 5'ten fazla işlem varsa kural ihlal edildi.

Redis yapısı:
  Key  : velocity:{user_id}
  Type : Sorted Set
  Score: Unix timestamp (float)
  Value: transaction_id
"""
import time
from shared.config import get_settings
from app.state.redis_client import redis_client

_s = get_settings()
LIMIT = 5
WINDOW = 60  # seconds


def check(user_id: str, tx_id: str, timestamp: float) -> bool:
    """
    Kural ihlal edildi mi? True = ihlal, False = temiz.
    Yan etki: mevcut transaction'ı Redis'e ekler, pencere dışını temizler.
    """
    key = f"velocity:{user_id}"
    now = timestamp

    pipe = redis_client.pipeline()
    # 1) Eski kayıtları temizle (window dışı)
    pipe.zremrangebyscore(key, "-inf", now - WINDOW)
    # 2) Yeni transaction'ı ekle
    pipe.zadd(key, {tx_id: now})
    # 3) Penceredeki toplam sayıyı al
    pipe.zcard(key)
    # 4) Key'e TTL ver (bellek sızıntısını önle)
    pipe.expire(key, WINDOW * 2)
    results = pipe.execute()

    count = results[2]  # zcard sonucu
    return count > LIMIT
