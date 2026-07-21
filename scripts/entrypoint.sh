#!/bin/sh
set -eu

# A temporarily unavailable database must not prevent Railway from starting the
# health endpoint. Handlers already report database failures without crashing.
if ! alembic upgrade head; then
  echo '{"event":"database_migration_failed","level":"warning","message":"starting in degraded mode"}' >&2
fi
exec python -m app.main
