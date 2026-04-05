#!/bin/bash

set -euo pipefail

VENV_PATH="${HOME}/.venvs/portfolio-manager"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Creating local virtualenv at ${VENV_PATH}"
mkdir -p "${HOME}/.venvs"

"${PYTHON_BIN}" -m venv "${VENV_PATH}"
"${VENV_PATH}/bin/python" -m pip install --upgrade pip
"${VENV_PATH}/bin/pip" install -r backend/requirements.txt

cat <<EOF

Local virtualenv is ready.

VS Code workspace settings already point to:
  ${VENV_PATH}/bin/python

To activate it in your shell:
  source "${VENV_PATH}/bin/activate"

To start the backend:
  cd backend && "${VENV_PATH}/bin/python" -m uvicorn main:app --reload --port 8000

EOF