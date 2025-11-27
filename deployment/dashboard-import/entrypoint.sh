#!/bin/sh
# Dashboard import script
#
# This script automates the import of OpenSearch dashboards from template files.
#
# Prerequisites:
#   - OpenSearch Dashboards must be accessible at http://dashboards:5601
#   - Admin credentials must be provided via OPENSEARCH_INITIAL_ADMIN_PASSWORD env var
#   - Dashboard template files must be present in /app/*.ndjson
#
# Steps performed:
#   1. Wait for dashboards service to initialize
#   2. Poll dashboards API until it's ready (with timeout)
#   3. Import all .ndjson dashboard files from /templates
#   4. Report success/failure for each import
#   5. Exit with status code based on results

# Configuration variables
CHECK_INTERVAL=10
MAX_ATTEMPTS=20
DASHBOARD_URL="http://dashboards:5601/api/status"
IMPORT_URL="http://dashboards:5601/api/saved_objects/_import?overwrite=true"

echo "Dashboard Import Starting..."
echo "Waiting for dashboards to be ready..."


# Check if dashboards is ready (with timeout)
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT + 1))
  
  if curl -sf -u "admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD}" \
    "$DASHBOARD_URL" >/dev/null 2>&1; then
    echo "Dashboards is ready (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    break
  fi
  
  if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "ERROR: Max attempts reached. Dashboards not ready after $MAX_ATTEMPTS attempts."
    echo "Dashboard service may not be running or credentials may be incorrect."
    exit 1
  fi
  
  sleep $CHECK_INTERVAL
done

echo "Starting dashboard import..."

SUCCESS=0
FAILED=0

for file in /app/*.ndjson; do
  [ -f "$file" ] || continue
  
  echo "Importing: $(basename $file)"
  
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$IMPORT_URL" \
    -u "admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD}" \
    -H "osd-xsrf: true" \
    -F "file=@$file")
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  
  if [ "$HTTP_CODE" = "200" ]; then
    echo "[OK] $(basename $file)"
    SUCCESS=$((SUCCESS + 1))
  else
    echo "[FAILED] $(basename $file) (HTTP $HTTP_CODE)"
    FAILED=$((FAILED + 1))
  fi
done


echo "Import complete: $SUCCESS successful, $FAILED failed"

[ $SUCCESS -gt 0 ] && exit 0 || exit 1

