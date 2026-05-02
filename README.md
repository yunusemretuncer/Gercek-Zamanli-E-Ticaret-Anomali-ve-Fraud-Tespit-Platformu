# 🛡 Fraud Detection Platform

Gerçek zamanlı işlem izleme ve anomali tespit sistemi. E-ticaret platformlarında gerçekleşen ödeme işlemlerini analiz ederek şüpheli davranışları tespit eder, canlı dashboard üzerinden görselleştirir ve AI ajanları için MCP arayüzü sunar.

---

## 📋 İçindekiler

- [Proje Amacı](#proje-amacı)
- [Sistem Mimarisi](#sistem-mimarisi)
- [Teknoloji Seçimleri](#teknoloji-seçimleri)
- [Anomali Tespit Mantığı](#anomali-tespit-mantığı)
- [Kurulum](#kurulum)
- [Kullanım Rehberi](#kullanım-rehberi)
- [API Dokümantasyonu](#api-dokümantasyonu)
- [MCP Dokümantasyonu](#mcp-dokümantasyonu)
- [Script Kullanımı](#script-kullanımı)
- [Sorun Giderme](#sorun-giderme)

---

## Proje Amacı

Bu platform üç temel ihtiyacı karşılar:

1. **Gerçek zamanlı tespit** — İşlem veritabanına düşmeden önce anomali kuralları çalıştırılır
2. **Canlı izleme** — WebSocket üzerinden anlık fraud alertleri dashboard'a iletilir
3. **AI entegrasyonu** — MCP Server sayesinde AI ajanları sistemi sorgulayabilir

---

## Sistem Mimarisi

```
┌─────────┐    POST /transactions     ┌──────────┐
│ Client  │ ─────────────────────────▶│   API    │
└─────────┘                           │ (FastAPI)│
     ▲                                └────┬─────┘
     │ WebSocket                           │ transaction.created
     │ fraud alertleri                     ▼
     │                              ┌──────────────┐
     │                              │  RabbitMQ    │
     │                              │ fraud.events │
     │                              └──┬────────┬──┘
     │                                 │        │
     │                    tx.created   │        │ fraud.detected
     │                                 ▼        │
     │                          ┌──────────┐    │
     │                          │  Worker  │────┘
     │                          │  (rules) │
     │                          └──┬────┬──┘
     │                             │    │
     │                             ▼    ▼
     │                       ┌─────┐  ┌────────┐
     │                       │Redis│  │Postgres│
     │                       └─────┘  └────────┘
     │                                    ▲
     └────────────────────────────────────┘
              WebSocket + REST reads
                      ▲
               ┌──────────────┐
               │  MCP Server  │
               │  (AI tools)  │
               └──────────────┘
```

### Servisler

| Servis | Görev | Port |
|--------|-------|------|
| **API** | HTTP ingestion, WebSocket, fraud alert consumer | 8000 |
| **Worker** | Fraud kural motoru, Redis state, Postgres güncelleme | — |
| **MCP Server** | AI ajan araçları (get_recent_frauds, check_user_status) | — |
| **Frontend** | React dashboard, canlı feed, grafikler | 3000 |
| **PostgreSQL** | İşlem ledger'ı | 5432 |
| **RabbitMQ** | Asenkron mesajlaşma | 5672 / 15672 |
| **Redis** | Kullanıcı bazlı davranış state'i | 6379 |

### Veri Akışı

1. Client → `POST /transactions` → API
2. API → Postgres'e yazar (commit)
3. API → RabbitMQ'ya `transaction.created` publish eder
4. Worker → `transactions_queue`'dan tüketir
5. Worker → Redis'ten kullanıcı state'ini okur, kuralları uygular
6. Worker → Postgres'te `is_fraud` günceller
7. Worker → Fraud ise `fraud.detected` publish eder
8. API → `fraud_alerts_queue`'dan tüketir → WebSocket ile frontend'e iletir

---

## Teknoloji Seçimleri

| Katman | Tercih | Gerekçe |
|--------|--------|---------|
| Backend | Python 3.12 + FastAPI | Async desteği, otomatik OpenAPI dokümantasyonu |
| Mesajlaşma | RabbitMQ | Topic exchange ile esnek routing, güvenilir delivery |
| Veritabanı | PostgreSQL 16 | ACID garantisi, UUID desteği, güçlü tip sistemi |
| Cache | Redis 7 | Sorted set ile sliding window, sub-millisecond okuma |
| Frontend | React + Recharts | Komponent mimarisi, WebSocket entegrasyonu |
| Container | Docker + Compose | Tek komutla tam sistem ayağa kaldırma |
| ORM | SQLAlchemy 2.0 | Typed `Mapped[]` API, psycopg 3 uyumu |
| Broker client | pika (sync) | Worker için yeterli, thread-safe lock ile API'de kullanılabilir |

### Cache Yönetimi Kararları

Redis üç ayrı yapı ile kullanılır:

- **`velocity:{user_id}`** → Sorted Set. Score = Unix timestamp, value = tx_id. `ZREMRANGEBYSCORE` ile pencere dışı kayıtlar temizlenir. O(log N) kompleksite.
- **`amt24h:{user_id}`** → Sorted Set. Mevcut transaction eklenmeden önce 24 saatlik penceredeki tutarların ortalaması hesaplanır. Ortalama her işlemde güncellenmez — pencere snapshot'ı alınır.
- **`lastloc:{user_id}`** → Hash. Son bilinen konum ve timestamp. Haversine mesafesi + süre ile imkansız seyahat tespiti yapılır.

---

## Anomali Tespit Mantığı

Bir işlem, aşağıdaki **3 kuraldan en az 2'sini** ihlal ederse fraud olarak işaretlenir.

### Kural 1 — Velocity (Hız)
Aynı kullanıcıdan son **60 saniye** içinde **5'ten fazla** işlem gelirse ihlal.

### Kural 2 — Amount (Tutar)
İşlem tutarı, kullanıcının son **24 saatteki ortalama** tutarının **3 katından** fazlaysa ihlal. Geçmişi olmayan kullanıcı için bu kural ateşlenmez.

### Kural 3 — Location (Konum)
Ardışık iki işlem arasındaki fiziksel mesafeyi katetmek için gereken minimum süre, gerçek süreyi aşıyorsa ihlal. Maksimum hız: **900 km/h** (uçak).

### Fraud Tespit Edildiğinde
- Postgres'te `is_fraud = true` set edilir
- `fraud.detected` eventi RabbitMQ'ya publish edilir
- API WebSocket üzerinden frontend'e iletir
- Dashboard'da kırmızı olarak işaretlenir

---

## Kurulum

### Gereksinimler

- Docker Desktop (Windows/Mac) veya Docker Engine (Linux)
- Git

### Hızlı Başlangıç

```bash
# Repoyu klonla
git clone <repo-url>
cd fraud-detection

# Sistemi ayağa kaldır
docker compose up --build
```

Servisler hazır olduğunda:

| Arayüz | URL |
|--------|-----|
| Dashboard | http://localhost:3000 |
| API Swagger | http://localhost:8000/docs |
| RabbitMQ UI | http://localhost:15672 (guest/guest) |

### Sistemi Durdurma

```bash
# Servisleri durdur
docker compose down

# Veritabanı dahil her şeyi temizle
docker compose down -v
```

---

## Kullanım Rehberi

### Dashboard

`http://localhost:3000` adresinde şunları görebilirsiniz:

- **Stat kartları** — Toplam işlem, fraud sayısı, fraud oranı
- **Fraud Oranı Grafiği** — 15 saniyelik dilimler halinde son 5 dakika
- **Canlı İşlem Akışı** — Tüm işlemler, fraud olanlar kırmızı
- **Fraud Alarm Paneli** — WebSocket üzerinden anlık alertler
- **Kullanıcı Görünümü** — user_id ile arama yaparak işlem geçmişi

### Manuel İşlem Gönderme

```bash
bash manual-input.sh <user_id> <amount> <location>

# Örnek
bash manual-input.sh user_42 199.90 "Istanbul, TR"
```

### Otomatik Test

```bash
bash auto-test.sh --duration=60 --rate=2 --anomaly-chance=30

# Parametreler
# --duration=<saniye>     Çalışma süresi (varsayılan: 60)
# --rate=<istek/saniye>   Saniyedeki istek sayısı (varsayılan: 2)
# --anomaly-chance=<%>    Anomali oluşturma olasılığı (varsayılan: 30)
```

---

## API Dokümantasyonu

Tam interaktif dokümantasyon: `http://localhost:8000/docs`

### Endpoints

#### `POST /transactions`
Yeni işlem oluşturur.

**Request Body:**
```json
{
  "user_id": "user_42",
  "amount": 199.90,
  "location": "Istanbul, TR",
  "timestamp": "2026-04-17T10:00:00Z"
}
```
`timestamp` opsiyonel — verilmezse sunucu zamanı kullanılır.

**Response (201):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_42",
  "amount": "199.90",
  "timestamp": "2026-04-17T10:00:00+00:00",
  "location": "Istanbul, TR",
  "is_fraud": false,
  "created_at": "2026-04-17T10:00:00.123456+00:00"
}
```

#### `GET /transactions?limit=500`
Son işlemleri listeler.

#### `GET /transactions/users/{user_id}`
Belirli kullanıcının tüm işlemlerini getirir.

#### `GET /health`
Sistem sağlık durumu.

```json
{
  "status": "ok",
  "database": "ok",
  "broker": "ok"
}
```

#### `WS /ws/transactions`
WebSocket bağlantısı. Fraud tespit edildiğinde şu formatta mesaj iletilir:

```json
{
  "transaction_id": "550e8400-...",
  "user_id": "user_42",
  "rules_violated": ["velocity", "amount"],
  "detected_at": "2026-04-17T10:00:01.500000+00:00"
}
```

---

## MCP Dokümantasyonu

MCP Server, AI ajanlarının sistemi sorgulamasını sağlar. `stdio` transport kullanır.

### Araçlar

#### `get_recent_frauds(limit=20)`
Son fraud işlemlerini listeler.

**Parametreler:**
- `limit` (int, opsiyonel): Döndürülecek maksimum kayıt sayısı. Varsayılan: 20.

**Örnek yanıt:**
```json
[
  {
    "transaction_id": "550e8400-...",
    "user_id": "user_42",
    "amount": 500.0,
    "location": "Istanbul, TR",
    "timestamp": "2026-04-17T10:00:00+00:00",
    "created_at": "2026-04-17T10:00:00.123456+00:00"
  }
]
```

#### `check_user_status(user_id)`
Kullanıcının risk durumunu ve işlem özetini döndürür.

**Parametreler:**
- `user_id` (str, zorunlu): Sorgulanacak kullanıcı kimliği.

**Örnek yanıt:**
```json
{
  "user_id": "user_42",
  "total_transactions": 150,
  "fraud_count": 12,
  "fraud_rate_pct": 8.0,
  "recent_24h": 45,
  "recent_velocity": 2,
  "avg_amount": 185.50,
  "risk": "LOW"
}
```

**Risk seviyeleri:**
- `HIGH` — Fraud oranı ≥ %30 veya son dakikada 5+ işlem
- `MEDIUM` — Fraud oranı ≥ %10
- `LOW` — Diğer

### MCP Test Yöntemi

```bash
docker exec -it fraud-detection-mcp-1 python -c "
import sys; sys.path.insert(0, '/srv')
from app.main import get_recent_frauds, check_user_status
print(get_recent_frauds(limit=3))
print(check_user_status('user_42'))
"
```

---

## Script Kullanımı

### `manual-input.sh`

Tek bir işlemi manuel olarak sisteme gönderir.

```bash
bash manual-input.sh <user_id> <amount> <location>
```

| Parametre | Açıklama | Örnek |
|-----------|----------|-------|
| `user_id` | Kullanıcı kimliği | `user_42` |
| `amount` | İşlem tutarı (> 0) | `199.90` |
| `location` | Konum | `"Istanbul, TR"` |

### `auto-test.sh`

Rastgele kullanıcılar ve anomali senaryoları oluşturarak sistemi yükler.

```bash
bash auto-test.sh [--duration=60] [--rate=2] [--anomaly-chance=30]
```

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `--duration` | Çalışma süresi (saniye) | 60 |
| `--rate` | Saniyedeki istek sayısı | 2 |
| `--anomaly-chance` | Anomali senaryosu olasılığı (%) | 30 |

**Anomali senaryoları:**
- **Velocity** — Aynı kullanıcıdan 7 işlem arka arkaya
- **Amount** — Önce 3 küçük işlem, ardından 7 büyük işlem (500.00)

---

## CI/CD

Proje, GitHub Actions ile otomatik CI pipeline'ına sahiptir. Her `main` branch'e push veya pull request açıldığında tetiklenir.

### Pipeline Adımları

1. **Checkout** — Kod repodan çekilir
2. **Docker Buildx** — Multi-platform build ortamı kurulur
3. **Build** — Tüm servisler (`docker compose build`) derlenir
4. **Smoke Test** — Altyapı servisleri (db, rabbitmq, redis) ayağa kaldırılır, API başlatılır, `GET /health` endpoint'i kontrol edilir
5. **Teardown** — Test ortamı temizlenir (`docker compose down -v`)

### Workflow Dosyası

`.github/workflows/ci.yml` — Her push'ta otomatik çalışır. GitHub Actions sekmesinden sonuçları takip edebilirsiniz.

```yaml
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

---

## Sorun Giderme

### `docker compose up --build` başarısız

```bash
# Docker Desktop çalışıyor mu?
docker info

# Portlar kullanımda mı?
# 8000, 3000, 5432, 5672, 15672, 6379 portlarını kontrol et
```

### Frontend veri göstermiyor

```bash
# API sağlık durumunu kontrol et
curl http://localhost:8000/health

# CORS sorunu olabilir — API'yi yeniden başlat
docker compose restart api
```

### Worker fraud tespit etmiyor

```bash
# Redis state'ini temizle (eski ortalamalar karışabilir)
docker exec -it fraud-detection-redis-1 redis-cli FLUSHDB

# Worker loglarını kontrol et
docker compose logs worker --tail=50
```

### RabbitMQ bağlantı hatası

```bash
# RabbitMQ hazır mı?
docker compose logs rabbitmq --tail=20

# Tüm servisleri yeniden başlat
docker compose restart
```

### Script çalışmıyor (Windows)

```bash
# CRLF satır sonu sorunu
bash -c "sed -i 's/\r//' manual-input.sh auto-test.sh"

# Sonra tekrar dene
bash manual-input.sh user_42 100 "Istanbul, TR"
```

### Postgres bağlantısı

```bash
# Veritabanına bağlan
docker exec -it fraud-detection-db-1 psql -U fraud -d fraud_db

# İşlemleri listele
SELECT id, user_id, amount, is_fraud FROM transactions LIMIT 10;
```
