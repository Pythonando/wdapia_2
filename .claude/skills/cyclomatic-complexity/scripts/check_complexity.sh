#!/usr/bin/env bash
# Atalho para rodar a análise de complexidade a partir da raiz do projeto.
#
#   .claude/skills/cyclomatic-complexity/scripts/check_complexity.sh
#   .claude/skills/cyclomatic-complexity/scripts/check_complexity.sh apps/payments
#   .claude/skills/cyclomatic-complexity/scripts/check_complexity.sh --changed origin/master
#
# Todos os argumentos são repassados para complexity_report.py.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

if [[ -x "$PROJECT_ROOT/venv/bin/python" ]]; then
  PY="$PROJECT_ROOT/venv/bin/python"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PY="$PROJECT_ROOT/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

cd "$PROJECT_ROOT" || exit 2
exec "$PY" "$SCRIPT_DIR/complexity_report.py" "$@"
