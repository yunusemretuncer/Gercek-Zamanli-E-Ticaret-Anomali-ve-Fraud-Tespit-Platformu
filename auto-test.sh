#!/usr/bin/env bash
# Usage: ./auto-test.sh [--duration=60] [--rate=2] [--anomaly-chance=30]

API_URL="${API_URL:-http://localhost:8000}"

# Defaults
DURATION=60
RATE=2
ANOMALY_CHANCE=30

# Parse args
for arg in "$@"; do
  case $arg in
    --duration=*)  DURATION="${arg#*=}" ;;
    --rate=*)      RATE="${arg#*=}" ;;
    --anomaly-chance=*) ANOMALY_CHANCE="${arg#*=}" ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

USERS=("user_A" "user_B" "user_C" "user_D" "user_E")
LOCATIONS=("Istanbul, TR" "Ankara, TR" "Izmir, TR" "London, UK" "Berlin, DE" "Paris, FR" "Dubai, AE")
SLEEP=$(echo "scale=4; 1 / $RATE" | bc)

echo "🚀 Auto-test started"
echo "   duration      : ${DURATION}s"
echo "   rate          : ${RATE} req/s"
echo "   anomaly-chance: ${ANOMALY_CHANCE}%"
echo "   sleep interval: ${SLEEP}s"
echo ""

START=$(date +%s)
COUNT=0
FRAUD_SENT=0

send_tx() {
  local user_id="$1"
  local amount="$2"
  local location="$3"
  curl -s -o /dev/null -X POST "$API_URL/transactions" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$user_id\", \"amount\": $amount, \"location\": \"$location\"}"
}

while true; do
  NOW=$(date +%s)
  ELAPSED=$(( NOW - START ))
  [ "$ELAPSED" -ge "$DURATION" ] && break

  # Random user ve location
  USER=${USERS[$RANDOM % ${#USERS[@]}]}
  LOC=${LOCATIONS[$RANDOM % ${#LOCATIONS[@]}]}

  # Anomali mi?
  ROLL=$(( RANDOM % 100 ))

  if [ "$ROLL" -lt "$ANOMALY_CHANCE" ]; then
    # Anomali senaryosu: velocity veya amount
    SCENARIO=$(( RANDOM % 2 ))

    if [ "$SCENARIO" -eq 0 ]; then
      # Velocity anomalisi: aynı kullanıcıdan hızlı 7 işlem
      echo "⚡ Velocity anomaly for $USER"
      for i in $(seq 1 7); do
        send_tx "$USER" "50.00" "$LOC"
      done
      FRAUD_SENT=$(( FRAUD_SENT + 1 ))
    else
      # Amount anomalisi: önce küçük, sonra büyük
      echo "💸 Amount anomaly for $USER"
      for i in $(seq 1 3); do
        send_tx "$USER" "10.00" "$LOC"
      done
      # Hızlıca büyük işlemler
      for i in $(seq 1 7); do
        send_tx "$USER" "500.00" "$LOC"
      done
      FRAUD_SENT=$(( FRAUD_SENT + 1 ))
    fi
  else
    # Normal işlem
    AMOUNT=$(echo "scale=2; ($RANDOM % 200) + 10" | bc)
    send_tx "$USER" "$AMOUNT" "$LOC"
  fi

  COUNT=$(( COUNT + 1 ))
  printf "\r   sent: %d transactions | anomalies: %d | elapsed: %ds" "$COUNT" "$FRAUD_SENT" "$ELAPSED"
  sleep "$SLEEP"
done

echo ""
echo ""
echo "✅ Test complete"
echo "   total batches : $COUNT"
echo "   anomaly batches: $FRAUD_SENT"
echo "   duration      : ${DURATION}s"
