#!/bin/sh
set -eu

PROJECT_DIR=${WHAT_CHANGES_PROJECT_DIR:-/opt/what_changes_postgresql}
BACKUP_ROOT=${WHAT_CHANGES_BACKUP_ROOT:?Set WHAT_CHANGES_BACKUP_ROOT to an external mounted path}
RETENTION_DAYS=${WHAT_CHANGES_BACKUP_RETENTION_DAYS:-35}
ALLOW_LOCAL=${WHAT_CHANGES_ALLOW_LOCAL_BACKUP:-0}

case "$RETENTION_DAYS" in
    ''|*[!0-9]*) echo "RETENTION_DAYS must be a non-negative integer" >&2; exit 2 ;;
esac

mkdir -p "$BACKUP_ROOT"
backup_root=$(realpath "$BACKUP_ROOT")
root_source=$(findmnt -n -o SOURCE -T /)
backup_source=$(findmnt -n -o SOURCE -T "$backup_root")
backup_fstype=$(findmnt -n -o FSTYPE -T "$backup_root")
if [ "$ALLOW_LOCAL" != "1" ]; then
    if [ "$root_source" = "$backup_source" ]; then
        echo "Refusing backup on the VM root filesystem: $backup_root" >&2
        echo "Mount external storage or set WHAT_CHANGES_ALLOW_LOCAL_BACKUP=1 for a disposable drill only." >&2
        exit 3
    fi
    case "$backup_fstype" in
        tmpfs|devtmpfs|overlay|squashfs)
            echo "Refusing non-persistent backup filesystem $backup_fstype: $backup_root" >&2
            exit 3
            ;;
    esac
fi

backup_base="$backup_root/what_changes_postgresql"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
partial_dir="$backup_base/.partial-$timestamp-$$"
final_dir="$backup_base/$timestamp"
mkdir -p "$partial_dir"
chmod 700 "$partial_dir"

cleanup_partial() {
    if [ -d "$partial_dir" ]; then
        rm -rf -- "$partial_dir"
    fi
}
trap cleanup_partial EXIT HUP INT TERM

cd "$PROJECT_DIR"
docker compose up -d db web >/dev/null
docker compose exec -T db sh -ec 'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --compress=6' > "$partial_dir/database.dump"
docker compose exec -T web tar --numeric-owner -czf - -C /app/data/source_snapshots . > "$partial_dir/source_snapshots.tar.gz"
docker compose exec -T web tar --numeric-owner -czf - -C /app/data/generated_reports . > "$partial_dir/generated_reports.tar.gz"

docker compose exec -T db pg_restore --list < "$partial_dir/database.dump" >/dev/null
tar -tzf "$partial_dir/source_snapshots.tar.gz" >/dev/null
tar -tzf "$partial_dir/generated_reports.tar.gz" >/dev/null

{
    release_id=${WHAT_CHANGES_RELEASE_ID:-$(git rev-parse HEAD 2>/dev/null || true)}
    if [ -z "$release_id" ]; then
        release_id=$(docker compose images -q web)
    fi
    printf 'created_utc=%s\n' "$timestamp"
    printf 'hostname=%s\n' "$(hostname)"
    printf 'project_dir=%s\n' "$PROJECT_DIR"
    printf 'release_id=%s\n' "$release_id"
    printf 'postgres_image=%s\n' "$(docker compose images -q db)"
    printf 'web_image=%s\n' "$(docker compose images -q web)"
} > "$partial_dir/metadata.txt"

(cd "$partial_dir" && sha256sum database.dump source_snapshots.tar.gz generated_reports.tar.gz metadata.txt > SHA256SUMS)
chmod 600 "$partial_dir"/*
mkdir -p "$backup_base"
mv "$partial_dir" "$final_dir"
trap - EXIT HUP INT TERM

if [ "$RETENTION_DAYS" -gt 0 ]; then
    find "$backup_base" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -mtime "+$RETENTION_DAYS" -exec rm -rf -- {} +
fi

printf 'backup=%s\n' "$final_dir"
du -sh "$final_dir"
