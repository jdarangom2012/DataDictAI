#!/usr/bin/env bash
# Respaldo diario de la base de datos propia de DataDict AI (no la de los
# clientes -- esta nunca se toca). Pensado para correr via cron en la VM,
# desde la raiz del repo: bash scripts/backup_db.sh
set -euo pipefail

BACKUP_DIR="$(dirname "$0")/../backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
FILE="$BACKUP_DIR/datadictai-$TIMESTAMP.sql.gz"

docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U "${POSTGRES_USER:-datadictai}" "${POSTGRES_DB:-datadictai}" \
    | gzip > "$FILE"

echo "Respaldo guardado en $FILE"

# Conserva solo los ultimos 14 dias de respaldos.
find "$BACKUP_DIR" -name "datadictai-*.sql.gz" -mtime +14 -delete
