#!/bin/sh
set -eu

PROJECT_DIR=${WHAT_CHANGES_PROJECT_DIR:-/opt/what_changes_postgresql}
DISK_PATH=${WHAT_CHANGES_DISK_PATH:-/}
DISK_WARNING_PERCENT=${WHAT_CHANGES_DISK_WARNING_PERCENT:-70}

case "$DISK_WARNING_PERCENT" in
    ''|*[!0-9]*) echo "DISK_WARNING_PERCENT must be an integer from 1 to 100" >&2; exit 2 ;;
esac
if [ "$DISK_WARNING_PERCENT" -lt 1 ] || [ "$DISK_WARNING_PERCENT" -gt 100 ]; then
    echo "DISK_WARNING_PERCENT must be an integer from 1 to 100" >&2
    exit 2
fi

disk_used=$(df -P "$DISK_PATH" | awk 'NR == 2 {gsub(/%/, "", $5); print $5}')
if [ -z "$disk_used" ]; then
    echo "Unable to read disk usage for $DISK_PATH" >&2
    exit 2
fi

status=0
if [ "$disk_used" -ge "$DISK_WARNING_PERCENT" ]; then
    echo "CRITICAL disk usage ${disk_used}% is at or above ${DISK_WARNING_PERCENT}% on $DISK_PATH" >&2
    status=1
else
    echo "OK disk usage ${disk_used}% is below ${DISK_WARNING_PERCENT}% on $DISK_PATH"
fi

cd "$PROJECT_DIR"
for service in db web; do
    container_id=$(docker compose ps -q "$service")
    if [ -z "$container_id" ]; then
        echo "CRITICAL service $service has no container" >&2
        status=1
        continue
    fi
    state=$(docker inspect --format '{{.State.Status}}' "$container_id")
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")
    if [ "$state" != "running" ] || [ "$health" != "healthy" ]; then
        echo "CRITICAL service $service state=$state health=$health" >&2
        status=1
    else
        echo "OK service $service state=$state health=$health"
    fi
done

exit "$status"
