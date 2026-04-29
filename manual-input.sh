#!/usr/bin/env bash
# Usage: ./manual-input.sh <user_id> <amount> <location>

set -e

API_URL="${API_URL:-http://localhost:8000}"

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <user_id> <amount> <location>"
  echo "Example: $0 user_42 199.90 'Istanbul, TR'"
  exit 1
fi

USER_ID="$1"
AMOUNT="$2"
LOCATION="$3"

echo "📤 Sending transaction..."
echo "   user_id  : $USER_ID"
echo "   amount   : $AMOUNT"
echo "   location : $LOCATION"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/transactions" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\", \"amount\": $AMOUNT, \"location\": \"$LOCATION\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "201" ]; then
  TX_ID=$(echo "$BODY" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
  IS_FRAUD=$(echo "$BODY" | grep -o '"is_fraud":[^,}]*' | cut -d':' -f2)
  echo "✅ Transaction created (HTTP $HTTP_CODE)"
  echo "   id       : $TX_ID"
  echo "   is_fraud : $IS_FRAUD"
else
  echo "❌ Failed (HTTP $HTTP_CODE)"
  echo "$BODY"
  exit 1
fi
