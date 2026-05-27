#!/usr/bin/env sh
# Author: kamekingdom (2026-05-27)

set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$SCRIPT_DIR/scripts/install_kamex.py" "$@"
