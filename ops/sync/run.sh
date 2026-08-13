#!/bin/sh
set -eu

PROJECT_DIR=${WHAT_CHANGES_PROJECT_DIR:-/opt/what_changes_postgresql}
cd "$PROJECT_DIR"

docker compose up -d db web
docker compose exec -T web python manage.py sync_releases --latest-majors 5
docker compose exec -T web python manage.py sync_version_support
docker compose exec -T web python manage.py parse_releases
docker compose exec -T web python manage.py classify_changes
