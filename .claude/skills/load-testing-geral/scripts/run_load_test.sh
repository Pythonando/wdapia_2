#!/usr/bin/env bash
# Orquestra um teste de carga ponta a ponta:
#   checagem de setup → build da stack → seed dos usuários → run do Locust →
#   relatório → gate.
#
#   ./run_load_test.sh --scenario baseline
#   ./run_load_test.sh --scenario stress --tags checkout
#   ./run_load_test.sh --host http://localhost:8000 --no-docker
#   ./run_load_test.sh --scenario baseline --with-worker --update-baseline
#
# Exit code: 0 = aprovado (ou com ressalvas), 1 = reprovado,
#            2 = uso inválido, 3 = skill ainda não configurada para o projeto.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SKILL_NAME="$(basename "$SKILL_DIR")"
PROJECT_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.loadtest.yml"

# Um nome por projeto: dois projetos com esta skill na mesma máquina não colidem.
PROJECT_NAME="$(basename "$PROJECT_ROOT" | tr -c 'a-zA-Z0-9\n' '-' | tr 'A-Z' 'a-z')"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-loadtest-$PROJECT_NAME}"
export LOADTEST_PROJECT_NAME="${LOADTEST_PROJECT_NAME:-$PROJECT_NAME}"
ENV_FILE="$SCRIPT_DIR/loadtest.env"

# Lê uma configuração: ambiente do shell > loadtest.env > default. O compose
# recebe o mesmo arquivo por --env-file, então os dois enxergam os mesmos valores.
cfg() {
  local name="$1" default="$2" value="${!1:-}"
  if [[ -z "$value" && -f "$ENV_FILE" ]]; then
    value="$(grep -E "^${name}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true)"
  fi
  echo "${value:-$default}"
}
APP_DIR="$(cfg LOADTEST_APP_DIR /app)"
CONTAINER_PORT="$(cfg LOADTEST_CONTAINER_PORT 8000)"
SERVER_CONFIG="$(cfg LOADTEST_SERVER_CONFIG '')"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SCENARIO="baseline"
USERS=""
SPAWN_RATE=""
RUN_TIME=""
HOST=""
TAGS=""
EXCLUDE_TAGS=""
USE_DOCKER=1
UPDATE_BASELINE=0
KEEP_UP=0
SEED_COUNT=""
ALLOW_EXPENSIVE=0
USER_CLASSES=""
WITH_REDIS=0
WITH_WORKER=0
SKIP_CHECK=0

usage() {
  sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  cat <<'EOT'

Opções:
  --scenario <smoke|baseline|stress|spike|soak>   Perfil de carga (default: baseline)
  --users N                Sobrescreve o nº de usuários virtuais
  --spawn-rate N           Sobrescreve a taxa de spawn (users/s)
  --run-time <5m|300s>     Sobrescreve a duração
  --host URL               Alvo (default: http://web:$LOADTEST_CONTAINER_PORT no Docker)
  --tags a,b               Só as tasks com essas tags
  --exclude-tags a,b       Ignora as tasks com essas tags
  --user-classes "A B"     Só estas classes de usuário virtual.
                           Use junto com --tags: se o filtro deixar uma classe
                           sem nenhuma task, o Locust derruba e respawna essa
                           classe em loop ("No tasks defined on ...") e o run
                           termina com 0 requests.
  --no-docker              Não sobe a stack; usa um alvo já no ar (requer locust local)
  --with-redis             Sobe também o Redis (cache/broker)
  --with-worker            Sobe também o worker (implica --with-redis);
                           exige LOADTEST_WORKER_COMMAND
  --seed-count N           Nº de usuários de teste a semear (default: = --users)
  --allow-expensive        Libera as tasks marcadas como caras (serviços pagos,
                           e-mail, cobrança). DESLIGADO por padrão.
  --update-baseline        Promove o resultado a baseline (só se não reprovar)
  --keep-up                Não derruba a stack ao final
  --skip-check             Ignora a checagem de setup (check_setup.py)
  -h, --help               Esta ajuda
EOT
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario)       SCENARIO="$2"; shift 2 ;;
    --users)          USERS="$2"; shift 2 ;;
    --spawn-rate)     SPAWN_RATE="$2"; shift 2 ;;
    --run-time)       RUN_TIME="$2"; shift 2 ;;
    --host)           HOST="$2"; shift 2 ;;
    --tags)           TAGS="$2"; shift 2 ;;
    --user-classes)   USER_CLASSES="$2"; shift 2 ;;
    --exclude-tags)   EXCLUDE_TAGS="$2"; shift 2 ;;
    --seed-count)     SEED_COUNT="$2"; shift 2 ;;
    --allow-expensive) ALLOW_EXPENSIVE=1; shift ;;
    --with-redis)     WITH_REDIS=1; shift ;;
    --with-worker)    WITH_WORKER=1; WITH_REDIS=1; shift ;;
    --no-docker)      USE_DOCKER=0; shift ;;
    --update-baseline) UPDATE_BASELINE=1; shift ;;
    --keep-up)        KEEP_UP=1; shift ;;
    --skip-check)     SKIP_CHECK=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    *) echo "Opção desconhecida: $1" >&2; usage; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# Setup do projeto: locustfile escrito, seed e loadtest.env configurados
# ---------------------------------------------------------------------------
if [[ $SKIP_CHECK -eq 0 ]]; then
  if ! python3 "$SCRIPT_DIR/check_setup.py"; then
    cat >&2 <<EOT

A skill '$SKILL_NAME' ainda não foi configurada para este projeto.
Acione o agente 'load-test-runner-geral': ele escreve o locustfile, os hooks do
seed e o loadtest.env lendo o código do projeto. (Ou faça à mão, seguindo
references/discovery-checklist.md.)
EOT
    exit 3
  fi
fi

# ---------------------------------------------------------------------------
# Perfis de carga
# ---------------------------------------------------------------------------
case "$SCENARIO" in
  smoke)    D_USERS=10;  D_SPAWN=2;  D_TIME=1m  ;;
  baseline) D_USERS=50;  D_SPAWN=5;  D_TIME=5m  ;;
  stress)   D_USERS=300; D_SPAWN=10; D_TIME=10m ;;
  spike)    D_USERS=200; D_SPAWN=50; D_TIME=3m  ;;
  soak)     D_USERS=30;  D_SPAWN=3;  D_TIME=30m ;;
  *) echo "Cenário inválido: $SCENARIO (use smoke|baseline|stress|spike|soak)" >&2; exit 2 ;;
esac

USERS="${USERS:-$D_USERS}"
SPAWN_RATE="${SPAWN_RATE:-$D_SPAWN}"
RUN_TIME="${RUN_TIME:-$D_TIME}"
SEED_COUNT="${SEED_COUNT:-$USERS}"
export LOADTEST_USER_POOL="$SEED_COUNT"

if [[ $ALLOW_EXPENSIVE -eq 1 ]]; then
  export LOADTEST_ALLOW_EXPENSIVE=1
  echo "AVISO: tasks caras habilitadas — este run pode chamar serviços pagos e gerar custo real." >&2
else
  export LOADTEST_ALLOW_EXPENSIVE=0
fi

PROFILES=()
[[ $WITH_REDIS -eq 1 ]]  && PROFILES+=(--profile redis)
[[ $WITH_WORKER -eq 1 ]] && PROFILES+=(--profile worker)
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ${PROFILES[@]+"${PROFILES[@]}"})

RUN_ID="$(date +%Y%m%dT%H%M%S)-${SCENARIO}"
REPORT_DIR="$SKILL_DIR/reports/$RUN_ID"
BASELINE_FILE="$SKILL_DIR/baselines/${SCENARIO}.json"
mkdir -p "$REPORT_DIR"

COMMIT="$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo desconhecido)"
BRANCH="$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo desconhecido)"

log() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }

cleanup() {
  if [[ $USE_DOCKER -eq 1 && $KEEP_UP -eq 0 ]]; then
    log "Derrubando a stack"
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

service_health() {
  "${COMPOSE[@]}" ps --format json "$1" 2>/dev/null \
    | python3 -c 'import json,sys
raw = sys.stdin.read().strip()
if not raw:
    print("unknown"); raise SystemExit
first = raw.splitlines()[0]
data = json.loads(first)
data = data[0] if isinstance(data, list) else data
print(data.get("Health") or data.get("State") or "unknown")' 2>/dev/null || echo unknown
}

wait_healthy() {
  local service="$1" tries="$2" state=unknown
  for _ in $(seq 1 "$tries"); do
    state="$(service_health "$service")"
    [[ "$state" == "healthy" ]] && return 0
    sleep 3
  done
  echo "ERRO: o serviço $service não ficou saudável (estado: $state). Logs:" >&2
  "${COMPOSE[@]}" logs --tail 60 "$service" >&2
  return 1
}

# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------
LOCUST_ARGS=(
  --headless
  --users "$USERS"
  --spawn-rate "$SPAWN_RATE"
  --run-time "$RUN_TIME"
  # Quem decide aprovado/reprovado é o analyze_results.py, com thresholds
  # explícitos — não o exit code padrão do Locust.
  --exit-code-on-error 0
)
[[ -n "$TAGS" ]]         && LOCUST_ARGS+=(--tags "${TAGS//,/ }")
[[ -n "$EXCLUDE_TAGS" ]] && LOCUST_ARGS+=(--exclude-tags "${EXCLUDE_TAGS//,/ }")

if [[ $USE_DOCKER -eq 1 ]]; then
  HOST="${HOST:-http://web:$CONTAINER_PORT}"

  DEPS=(db)
  [[ $WITH_REDIS -eq 1 ]] && DEPS+=(redis)
  log "Subindo ${DEPS[*]}"
  "${COMPOSE[@]}" up -d "${DEPS[@]}"
  for svc in "${DEPS[@]}"; do wait_healthy "$svc" 40; done

  APP=(web)
  [[ $WITH_WORKER -eq 1 ]] && APP+=(worker)
  log "Subindo ${APP[*]}"
  "${COMPOSE[@]}" up -d --build "${APP[@]}"
  wait_healthy web 60

  log "Semeando $SEED_COUNT usuários de teste"
  "${COMPOSE[@]}" exec -T web python \
    "$APP_DIR/.claude/skills/$SKILL_NAME/scripts/seed_load_test_users.py" \
    --count "$SEED_COUNT"

  log "Rodando Locust — $SCENARIO: $USERS usuários, spawn $SPAWN_RATE/s, $RUN_TIME"
  "${COMPOSE[@]}" run --rm \
    -e LOADTEST_USER_POOL="$SEED_COUNT" \
    -e LOADTEST_ALLOW_EXPENSIVE="${LOADTEST_ALLOW_EXPENSIVE}" \
    locust \
    -f /mnt/locust/locustfile.py \
    --host "$HOST" \
    "${LOCUST_ARGS[@]}" \
    --csv "/mnt/results/$RUN_ID/run" \
    --html "/mnt/results/$RUN_ID/run.html" \
    ${USER_CLASSES:+$USER_CLASSES} || true
else
  HOST="${HOST:?--no-docker exige --host}"
  command -v locust >/dev/null 2>&1 || LOCUST_BIN="uvx locust"
  LOCUST_BIN="${LOCUST_BIN:-locust}"

  log "Rodando Locust contra $HOST — $USERS usuários, $RUN_TIME"
  $LOCUST_BIN -f "$SCRIPT_DIR/locustfile.py" \
    --host "$HOST" \
    "${LOCUST_ARGS[@]}" \
    --csv "$REPORT_DIR/run" \
    --html "$REPORT_DIR/run.html" \
    ${USER_CLASSES:+$USER_CLASSES} || true
fi

# ---------------------------------------------------------------------------
# Relatório + gate
# ---------------------------------------------------------------------------
log "Gerando relatório"

ANALYZE_ARGS=(
  --csv-prefix "$REPORT_DIR/run"
  --baseline "$BASELINE_FILE"
  --output "$REPORT_DIR/RELATORIO.md"
  --scenario "$SCENARIO"
  --host "$HOST"
  --users "$USERS"
  --spawn-rate "$SPAWN_RATE"
  --run-time "$RUN_TIME"
  --tags "$TAGS"
  --commit "$COMMIT"
  --branch "$BRANCH"
  --project "$LOADTEST_PROJECT_NAME"
)
[[ -n "$SERVER_CONFIG" ]] && ANALYZE_ARGS+=(--server-config "$SERVER_CONFIG")
[[ $UPDATE_BASELINE -eq 1 ]] && ANALYZE_ARGS+=(--update-baseline)

set +e
python3 "$SCRIPT_DIR/analyze_results.py" "${ANALYZE_ARGS[@]}"
GATE=$?
set -e

echo
echo "Artefatos em: $REPORT_DIR"
echo "  RELATORIO.md  — relatório completo"
echo "  run.html      — dashboard interativo do Locust"
echo "  run_*.csv     — dados crus"
echo "  result.json   — métricas estruturadas"

exit $GATE
