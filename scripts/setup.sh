#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m venv .venv
PIP_CACHE_DIR="$PWD/.cache/pip" .venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip check
.venv/bin/python -m unittest discover -s tests -v
