#!/bin/sh
# Dedicated preview backup only; no other databases touched. Retention is manual.
set -eu
umask 077
stamp=$(date -u +%Y%m%dT%H%M%SZ)
target=/opt/hms/backups/hms-preview-$stamp.dump
docker exec hms-preview-db-1 pg_dump -U hms_db_admin -d hms_preview -Fc > "$target.part"
test -s "$target.part"
mv "$target.part" "$target"
sha256sum "$target" > "$target.sha256"
