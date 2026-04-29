"""
Amount Rule
───────────
İşlem tutarı, kullanıcının son 24 saatlik ortalama tutarının 3 katından
fazlaysa kural ihlal edildi. Geçmişi yoksa kural ateşlenmez.

Redis yapısı:
  Key  : amt24h:{user_id}
  Type : Sorted Set
  Score: Unix timestamp
  Value: "{tx_id}:{amount}"
"""
from decimal import Decimal
from app.state.redis_client import redis_client

MULTIPLIER = Decimal("3.0")
WINDOW = 86400  # 24 saat


def check(user_id: str, tx_id: str, amount: Decimal, timestamp: float) -> bool:
    key = f"amt24h:{user_id}"
    window_start = timestamp - WINDOW

    pipe = redis_client.pipeline()
    # 1) Pencere dışındaki eski kayıtları temizle
    pipe.zremrangebyscore(key, "-inf", window_start)
    # 2) Penceredeki mevcut kayıtları al (henüz bu tx eklenmeden)
    pipe.zrange(key, 0, -1)
    # 3) Bu transaction'ı ekle
    pipe.zadd(key, {f"{tx_id}:{amount}": timestamp})
    pipe.expire(key, WINDOW * 2)
    results = pipe.execute()

    existing = results[1]  # zrange sonucu

    if not existing:
        # Geçmiş yok — kural ateşlenemez
        return False

    # Member formatı: "tx_id:amount" — amount kısmını parse et
    amounts = []
    for member in existing:
        try:
            amounts.append(Decimal(member.split(":", 1)[1]))
        except Exception:
            pass

    if not amounts:
        return False

    average = sum(amounts) / len(amounts)
    return amount > MULTIPLIER * average