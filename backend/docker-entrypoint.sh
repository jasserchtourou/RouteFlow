#!/bin/sh
# Apply pending migrations, then start the given command. Set RUN_MIGRATIONS=0 to skip
# (e.g. for one-off commands such as the seed script).
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    alembic upgrade head
fi

exec "$@"
