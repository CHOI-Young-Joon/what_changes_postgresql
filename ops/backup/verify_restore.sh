#!/bin/sh
set -eu

PROJECT_DIR=${WHAT_CHANGES_PROJECT_DIR:-/opt/what_changes_postgresql}
BACKUP_DIR=${1:?Usage: verify_restore.sh BACKUP_DIRECTORY}
backup_dir=$(realpath "$BACKUP_DIR")

for required in database.dump source_snapshots.tar.gz generated_reports.tar.gz metadata.txt SHA256SUMS; do
    if [ ! -f "$backup_dir/$required" ]; then
        echo "Missing backup file: $required" >&2
        exit 2
    fi
done

(cd "$backup_dir" && sha256sum -c SHA256SUMS)
tar -tzf "$backup_dir/source_snapshots.tar.gz" >/dev/null
tar -tzf "$backup_dir/generated_reports.tar.gz" >/dev/null

cd "$PROJECT_DIR"
docker compose up -d db >/dev/null
verify_db="what_changes_verify_$(date -u +%Y%m%d%H%M%S)_$$"

drop_verify_db() {
    docker compose exec -T -e VERIFY_DB="$verify_db" db sh -ec 'dropdb --username="$POSTGRES_USER" --if-exists "$VERIFY_DB"' >/dev/null 2>&1 || true
}
trap drop_verify_db EXIT HUP INT TERM

docker compose exec -T -e VERIFY_DB="$verify_db" db sh -ec 'createdb --username="$POSTGRES_USER" "$VERIFY_DB"'
docker compose exec -T -e VERIFY_DB="$verify_db" db sh -ec 'pg_restore --username="$POSTGRES_USER" --dbname="$VERIFY_DB" --exit-on-error --no-owner --no-privileges' < "$backup_dir/database.dump"
docker compose exec -T -e VERIFY_DB="$verify_db" db sh -ec 'psql --username="$POSTGRES_USER" --dbname="$VERIFY_DB" --tuples-only --no-align --command="SELECT COUNT(*) FROM releases_release; SELECT COUNT(*) FROM releases_sourcesnapshot; SELECT COUNT(*) FROM releases_changeitem;"'

drop_verify_db
trap - EXIT HUP INT TERM
printf 'restore_verification=success\nbackup=%s\n' "$backup_dir"
