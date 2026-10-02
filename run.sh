#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export LD_LIBRARY_PATH="/usr/local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec .venv/bin/python -m voice2fritz.main "$@"
