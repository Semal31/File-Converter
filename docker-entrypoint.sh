#!/bin/bash
set -e

PUID="${PUID:-99}"
PGID="${PGID:-100}"

# Create/update group
if getent group appuser > /dev/null 2>&1; then
    groupmod -o -g "$PGID" appuser
else
    groupadd -o -g "$PGID" appuser
fi

# Create/update user
if id appuser > /dev/null 2>&1; then
    usermod -o -u "$PUID" -g appuser appuser
else
    useradd -o -u "$PUID" -g appuser -d /app -s /bin/bash appuser
fi

# Ensure data directory exists with correct ownership
mkdir -p /app/data
chown appuser:appuser /app/data

echo "Starting file-converter as UID=$PUID GID=$PGID"

exec gosu appuser "$@"
