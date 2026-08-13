#!/bin/sh
set -eu

PROJECT_DIR=${WHAT_CHANGES_PROJECT_DIR:-/opt/what_changes_postgresql}
BACKUP_DIR=${1:?Usage: drill_full_restore.sh BACKUP_DIRECTORY}
DRILL_PROJECT=${WHAT_CHANGES_DRILL_PROJECT:-what_changes_restore_drill}
backup_dir=$(realpath "$BACKUP_DIR")

if [ "$DRILL_PROJECT" = "what_changes_postgresql" ]; then
    echo "Refusing to use the production Compose project for a restore drill" >&2
    exit 2
fi

for required in database.dump source_snapshots.tar.gz generated_reports.tar.gz metadata.txt SHA256SUMS; do
    if [ ! -f "$backup_dir/$required" ]; then
        echo "Missing backup file: $required" >&2
        exit 2
    fi
done
(cd "$backup_dir" && sha256sum -c SHA256SUMS)

cd "$PROJECT_DIR"
export COMPOSE_PROJECT_NAME="$DRILL_PROJECT"

cleanup_drill() {
    docker compose down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup_drill EXIT HUP INT TERM

cleanup_drill
docker compose up -d --wait db

docker compose exec -T db sh -ec 'dropdb --username="$POSTGRES_USER" --if-exists "$POSTGRES_DB"'
docker compose exec -T db sh -ec 'createdb --username="$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T db sh -ec 'pg_restore --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --exit-on-error --no-owner --no-privileges' < "$backup_dir/database.dump"

docker compose run --rm --no-deps --user 0:0 -T data-init sh -ec 'tar --no-same-owner --no-same-permissions -xzf - -C /app/data/source_snapshots && chown -R 1000:1000 /app/data/source_snapshots' < "$backup_dir/source_snapshots.tar.gz"
docker compose run --rm --no-deps --user 0:0 -T data-init sh -ec 'tar --no-same-owner --no-same-permissions -xzf - -C /app/data/generated_reports && chown -R 1000:1000 /app/data/generated_reports' < "$backup_dir/generated_reports.tar.gz"

counts=$(docker compose exec -T db sh -ec 'psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --tuples-only --no-align --command="SELECT COUNT(*) FROM releases_release; SELECT COUNT(*) FROM releases_sourcesnapshot; SELECT COUNT(*) FROM releases_changeitem;"')
snapshot_files=$(docker compose run --rm --no-deps -T data-init sh -ec 'find /app/data/source_snapshots -type f | wc -l')
report_files=$(docker compose run --rm --no-deps -T data-init sh -ec 'find /app/data/generated_reports -type f | wc -l')

docker compose up -d --wait web
web_container=$(docker compose ps -q web)
docker network disconnect "${DRILL_PROJECT}_outbound" "$web_container"
health=$(docker compose exec -T web python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/", timeout=5).read().decode())')
comparison_items=$(docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings web python -c 'import django; django.setup(); from releases.comparison import build_comparison_summary; print(build_comparison_summary("9.2.10", "18.4")["change_item_count"])')

printf '%s\n' "$counts"
printf 'source_snapshot_files=%s\n' "$snapshot_files"
printf 'generated_report_files=%s\n' "$report_files"
printf 'outbound_network=disconnected\n'
printf 'web_health=%s\n' "$health"
printf 'comparison_items_9.2.10_to_18.4=%s\n' "$comparison_items"
printf 'full_restore_drill=success\ncompose_project=%s\n' "$DRILL_PROJECT"

cleanup_drill
trap - EXIT HUP INT TERM
