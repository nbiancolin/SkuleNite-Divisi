#!/usr/bin/env bash
# Reinstall local packages from bind mounts so the container always matches the repo
# (editable installs in the image can otherwise lag behind mounted source).
set -euo pipefail
pip install -q -e /app/packages/musescore-part-formatter -e /app/packages/musescore-score-diff
exec "$@"
