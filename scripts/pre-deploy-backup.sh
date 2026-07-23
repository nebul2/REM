#!/usr/bin/env bash
# Run on the production server BEFORE deploying a new REM version.
# Snapshots everything needed to revert to the currently-running system:
#   - tags the running images as :prod-backup (instant rollback, no rebuild)
#   - records the current git commit
#   - dumps the TimescaleDB and copies the admin JSON state files
#
#   ./scripts/pre-deploy-backup.sh
#
# Rollback later (see end of output) restores the exact running binaries.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$ROOT/backups/$STAMP"; mkdir -p "$OUT"

echo "==> 1/4 tag running images as :prod-backup (fast rollback target)"
for img in rem-admin rem-collector; do
  docker tag "ghcr.io/nebul2/$img:latest" "ghcr.io/nebul2/$img:prod-backup" \
    && echo "    tagged $img:prod-backup" || echo "    (skip $img — no current image)"
done

echo "==> 2/4 record current git commit"
git rev-parse HEAD 2>/dev/null | tee "$OUT/git-commit.txt" || echo "(not a git clone)"
git rev-parse --abbrev-ref HEAD 2>/dev/null | tee "$OUT/git-branch.txt" || true

echo "==> 3/4 dump TimescaleDB"
docker exec stats-timescaledb pg_dump -U "${POSTGRES_USER:-gos}" "${POSTGRES_DB:-gos_rem}" \
  > "$OUT/gos_rem.sql" && echo "    -> $OUT/gos_rem.sql ($(wc -l < "$OUT/gos_rem.sql") lines)"

echo "==> 4/4 copy admin JSON state (experiments, groups, tokens, registry)"
docker cp stats-admin:/app/data "$OUT/admin-data" && echo "    -> $OUT/admin-data"

echo
echo "Backup complete: $OUT"
echo
echo "TO ROLLBACK to this exact running system:"
echo "  # fast (restore the exact binaries, no rebuild):"
echo "  docker compose down"
echo "  docker tag ghcr.io/nebul2/rem-admin:prod-backup     ghcr.io/nebul2/rem-admin:latest"
echo "  docker tag ghcr.io/nebul2/rem-collector:prod-backup ghcr.io/nebul2/rem-collector:latest"
echo "  docker compose up -d          # NOTE: no --build"
echo
echo "  # clean (rebuild the previous code):"
echo "  git checkout \$(cat $OUT/git-branch.txt)  &&  ./scripts/deploy-linode.sh"
echo
echo "  # data is on persistent volumes and untouched by deploy; restore only if needed:"
echo "  cat $OUT/gos_rem.sql | docker exec -i stats-timescaledb psql -U ${POSTGRES_USER:-gos} ${POSTGRES_DB:-gos_rem}"
