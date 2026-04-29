"""
Location Rule
─────────────
İki ardışık işlem arasındaki süre, iki lokasyon arasındaki mesafeyi
katetmek için fiziksel olarak imkansızsa kural ihlal edildi.

Varsayım: Maksimum hız 900 km/h (uçak).
Lokasyon "Şehir, Ülke" formatında gelir. Koordinat için basit bir
şehir→koordinat sözlüğü kullanıyoruz (portfolio kapsamı).

Redis yapısı:
  Key  : lastloc:{user_id}
  Type : Hash
  Fields: city, lat, lon, ts
"""
import math
import time
from app.state.redis_client import redis_client

MAX_SPEED_KMH = 900.0  # uçak hızı

# Basit şehir koordinat tablosu (genişletilebilir)
CITY_COORDS: dict[str, tuple[float, float]] = {
    "istanbul":  (41.0082, 28.9784),
    "ankara":    (39.9334, 32.8597),
    "izmir":     (38.4192, 27.1287),
    "antalya":   (36.8969, 30.7133),
    "bursa":     (40.1826, 29.0665),
    "london":    (51.5074, -0.1278),
    "paris":     (48.8566, 2.3522),
    "berlin":    (52.5200, 13.4050),
    "new york":  (40.7128, -74.0060),
    "tokyo":     (35.6762, 139.6503),
    "dubai":     (25.2048, 55.2708),
    "moscow":    (55.7558, 37.6173),
}


def _get_coords(location: str) -> tuple[float, float] | None:
    city = location.split(",")[0].strip().lower()
    return CITY_COORDS.get(city)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def check(user_id: str, location: str, timestamp: float) -> bool:
    key = f"lastloc:{user_id}"
    last = redis_client.hgetall(key)

    coords = _get_coords(location)

    # Her durumda mevcut lokasyonu güncelle
    if coords:
        pipe = redis_client.pipeline()
        pipe.hset(key, mapping={
            "city": location,
            "lat": coords[0],
            "lon": coords[1],
            "ts": timestamp,
        })
        pipe.expire(key, 86400)
        pipe.execute()

    # Önceki kayıt yoksa veya koordinat bilinmiyorsa kural ateşlenemez
    if not last or coords is None:
        return False

    prev_coords = (float(last["lat"]), float(last["lon"]))
    prev_ts = float(last["ts"])

    distance_km = _haversine_km(*prev_coords, *coords)
    elapsed_hours = (timestamp - prev_ts) / 3600.0

    if elapsed_hours <= 0:
        return False

    required_speed = distance_km / elapsed_hours
    return required_speed > MAX_SPEED_KMH
