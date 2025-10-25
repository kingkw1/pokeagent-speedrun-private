#!/bin/bash
# pytest runner that uses the correct virtual environment

cd "$(dirname "$0")/.."
source .venv/bin/activate
exec python -m pytest "$@"
