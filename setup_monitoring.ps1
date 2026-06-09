# Monitoring klasörleri
New-Item -ItemType Directory -Force -Path "monitoring/grafana/provisioning/datasources" | Out-Null
New-Item -ItemType Directory -Force -Path "monitoring/grafana/provisioning/dashboards" | Out-Null
New-Item -ItemType Directory -Force -Path "monitoring/grafana/dashboards" | Out-Null

# Prometheus config
Set-Content "monitoring/prometheus.yml" @'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fraud-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
'@

# Grafana datasource
Set-Content "monitoring/grafana/provisioning/datasources/prometheus.yml" @'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
'@

# Grafana dashboard provisioning
Set-Content "monitoring/grafana/provisioning/dashboards/default.yml" @'
apiVersion: 1
providers:
  - name: default
    folder: Fraud Detection
    type: file
    options:
      path: /var/lib/grafana/dashboards
'@

# Grafana dashboard JSON
Set-Content "monitoring/grafana/dashboards/fraud.json" @'
{
  "title": "Fraud Detection Platform",
  "uid": "fraud-detection",
  "version": 1,
  "schemaVersion": 38,
  "panels": [
    {
      "id": 1,
      "title": "HTTP Request Rate",
      "type": "timeseries",
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
      "targets": [{
        "expr": "rate(http_requests_total[1m])",
        "legendFormat": "{{method}} {{endpoint}}"
      }]
    },
    {
      "id": 2,
      "title": "Fraud Detected Total",
      "type": "stat",
      "gridPos": { "h": 4, "w": 6, "x": 12, "y": 0 },
      "targets": [{
        "expr": "fraud_detected_total",
        "legendFormat": "Fraud Count"
      }]
    },
    {
      "id": 3,
      "title": "Transactions Total",
      "type": "stat",
      "gridPos": { "h": 4, "w": 6, "x": 18, "y": 0 },
      "targets": [{
        "expr": "transactions_created_total",
        "legendFormat": "Transactions"
      }]
    },
    {
      "id": 4,
      "title": "Request Latency (p95)",
      "type": "timeseries",
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 4 },
      "targets": [{
        "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
        "legendFormat": "p95 latency"
      }]
    },
    {
      "id": 5,
      "title": "Active WebSocket Connections",
      "type": "stat",
      "gridPos": { "h": 4, "w": 6, "x": 0, "y": 8 },
      "targets": [{
        "expr": "websocket_connections_active",
        "legendFormat": "Active WS"
      }]
    }
  ],
  "time": { "from": "now-30m", "to": "now" },
  "refresh": "10s"
}
'@

# API requirements.txt — prometheus-fastapi-instrumentator ekle
$req = Get-Content "backend/api/requirements.txt" -Raw
if ($req -notmatch "prometheus") {
    Add-Content "backend/api/requirements.txt" "prometheus-fastapi-instrumentator==7.0.0"
}

# API main.py — metrics endpoint ekle
$main = Get-Content "backend/api/app/main.py" -Raw
if ($main -notmatch "Instrumentator") {
    $main = $main -replace "from fastapi.middleware.cors import CORSMiddleware", "from fastapi.middleware.cors import CORSMiddleware`nfrom prometheus_fastapi_instrumentator import Instrumentator"
    $main = $main -replace "app\.include_router\(health\.router\)", "app.include_router(health.router)`n`n# Prometheus metrics`nInstrumentator().instrument(app).expose(app)"
    Set-Content "backend/api/app/main.py" $main
}

# docker-compose.yml — prometheus + grafana ekle
$compose = Get-Content "docker-compose.yml" -Raw
$monitoringBlock = @'

  prometheus:
    image: prom/prometheus:v2.51.0
    restart: unless-stopped
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    depends_on:
      - api

  grafana:
    image: grafana/grafana:10.4.0
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    ports:
      - "3001:3000"
    depends_on:
      - prometheus

'@
$compose = $compose -replace "volumes:\r?\n  postgres_data:", "$monitoringBlock`nvolumes:`n  postgres_data:"
$compose = $compose -replace "volumes:\r?\n  redis_data:", "volumes:`n  redis_data:`n  grafana_data:"
Set-Content "docker-compose.yml" $compose

Write-Host "✅ Monitoring dosyaları oluşturuldu." -ForegroundColor Green
Write-Host "▶  Şimdi çalıştır: docker compose up --build" -ForegroundColor Cyan
Write-Host "   Prometheus : http://localhost:9090" -ForegroundColor Yellow
Write-Host "   Grafana    : http://localhost:3001 (admin/admin)" -ForegroundColor Yellow