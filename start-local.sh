#!/usr/bin/env bash

set -e

APP_HOST="fraud.deneme"
APP_URL="http://${APP_HOST}"

echo "[1/5] Minikube kontrol ediliyor..."

if ! minikube status >/dev/null 2>&1; then
  echo "Minikube çalışmıyor, başlatılıyor..."
  minikube start
else
  echo "Minikube zaten çalışıyor."
fi


echo "[2/5] ingress-nginx controller kontrol ediliyor..."

kubectl get pods -n ingress-nginx >/dev/null 2>&1 || {
  echo "ingress-nginx bulunamadı."
  exit 1
}


echo "[3/5] Ingress controller LoadBalancer yapılıyor..."

kubectl patch svc ingress-nginx-controller \
  -n ingress-nginx \
  -p '{"spec":{"type":"LoadBalancer"}}' \
  >/dev/null


echo "[4/5] minikube tunnel kontrol ediliyor..."

if pgrep -f "minikube tunnel" >/dev/null; then
  echo "minikube tunnel zaten çalışıyor."
else
  echo "minikube tunnel başlatılıyor..."

  nohup minikube tunnel \
    > /tmp/minikube-tunnel.log \
    2>&1 &

  sleep 3
fi


echo "[5/5] Uygulama açılıyor..."

if grep -q "127.0.0.1.*${APP_HOST}" /etc/hosts; then
  echo "/etc/hosts kaydı mevcut."
else
  echo "Hosts kaydı ekleniyor."
  echo "127.0.0.1 ${APP_HOST}" | sudo tee -a /etc/hosts >/dev/null
fi


echo
echo "Frontend: ${APP_URL}/docs"
echo "Swagger : ${APP_URL}/api/docs"
echo

# WSL içinde browser açmayı dene
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "${APP_URL}/docs" >/dev/null 2>&1 &
else
  echo "WSL içinde GUI browser bulunamadı."
  echo "Frontend'i şu adresten açabilirsin:"
  echo "${APP_URL}"
fi