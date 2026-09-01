#!/bin/sh
set -eu

if [ "${AGAS_MIGRATE_ON_STARTUP:-false}" = "true" ]; then
  alembic upgrade head
fi

exec "$@"
