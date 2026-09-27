# Observabilidade (Elastic Stack) — Guia Completo

## 🚀 Quick Start

### 1. Subir Stack
```bash
cd observability
cp .env.example .env            # configure senhas se necessário
sudo sysctl -w vm.max_map_count=262144
docker compose up -d --build    # primeira execução leva alguns minutos
```

### 2. Subir Django
Na raiz do projeto, escutando em todas as interfaces para o Heartbeat alcançar:
```bash
cp .env.example .env            # copiar variáveis de ambiente
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### 3. Acessar Kibana
- **URL**: http://localhost:5601
- **Usuário**: `elastic`
- **Senha**: valor de `ELASTIC_PASSWORD` em `observability/.env`

## 🔧 Variáveis de Ambiente

### Na raiz (`.env`)
```env
# APM - Rastreamento de requisições e spans
ELASTIC_APM_SERVER_URL=http://localhost:8200
ELASTIC_APM_SERVICE_NAME=django-app
ELASTIC_APM_ENVIRONMENT=development
ELASTIC_APM_TRANSACTION_SAMPLE_RATE=1.0
ELASTIC_APM_SECRET_TOKEN=

# Logging - Configuração de logs estruturados
LOG_DIR=observability/app-logs
LOG_LEVEL=DEBUG
SLOW_REQUEST_THRESHOLD=1000

# App - Integração com health check
APP_HEALTH_URL=http://host.docker.internal:8000/health/
```

**Importante**: `LOG_DIR` aponta para a mesma pasta de `APP_LOG_DIR` da stack (padrão `observability/app-logs`).

### Principais variáveis
| Var | Descrição |
|-----|-----------|
| `ELASTIC_APM_SERVER_URL` | URL do APM Server (padrão: localhost:8200) |
| `ELASTIC_APM_SERVICE_NAME` | Nome da aplicação no APM (ex: django-app) |
| `ELASTIC_APM_ENVIRONMENT` | Ambiente (development, staging, production) |
| `ELASTIC_APM_TRANSACTION_SAMPLE_RATE` | % de requisições a rastrear (1.0 = 100%, 0.1 = 10%) |
| `LOG_DIR` | Diretório para arquivos de log JSON |
| `LOG_LEVEL` | Nível mínimo de log (DEBUG, INFO, WARNING, ERROR) |
| `SLOW_REQUEST_THRESHOLD` | Latência (ms) que dispara aviso (padrão: 1000ms) |

## 📡 Componentes da Integração

### 1. Elastic APM (Rastreamento de Requisições)
- **Middleware**: `elasticapm.contrib.django.middleware.TracingMiddleware` (primeiro middleware)
- **O que captura**: 
  - Transações HTTP (método, path, status, duração)
  - Spans automáticos de SQL, templates, cache
  - Erros não tratados (5xx)
  - Contexto do usuário (user_id, username)
- **Índices**: `traces-apm*`, `logs-apm.error*`

### 2. Logging Estruturado (JSON + Correlação)
- **Arquivo**: `core/logging_config.py`
- **Formato**: JSON com `timestamp`, `level`, `message`, `trace.id`, `transaction.id`
- **Handlers**: Console (stdout) + Arquivo em `LOG_DIR/django.log`
- **RotatingFileHandler**: Limita a 10MB, cria até 5 backups
- **Injeção de APM**: Cada log inclui `trace.id` e `transaction.id` para correlação automática
- **Índices**: `filebeat-*` (logs são enviados pelo Filebeat)

### 3. Request Tracking Middleware
- **Arquivo**: `core/middleware.py` (registrado logo após APM)
- **O que faz**:
  - Gera/propaga `X-Request-ID` (UUID único por requisição)
  - Loga em JSON: método, path, status, duração, user_id, IP, user-agent
  - Marca requisições lentas como WARNING (> SLOW_REQUEST_THRESHOLD)
  - Marca 5xx como ERROR
  - Inicia `elasticapm.label()` com request_id
  - Seta contexto de usuário via `elasticapm.set_user_context()`
  - Adiciona header `Server-Timing` na resposta

### 4. Health Check (`/health/`)
- **Arquivo**: `core/views.py`
- **Endpoint**: `GET /health/`
- **O que retorna**:
  - HTTP 200 + JSON `{"status": "ok"}` se banco está OK
  - HTTP 503 + JSON `{"status": "error", "detail": "..."}` se banco falha
- **Monitorado por**: Heartbeat (cada 10s, aprox.)
- **Visto em**: Kibana → Uptime/Synthetics

### 5. Eventos de Negócio (Logs Estruturados)
- **Arquivo**: `produtos/views.py`
- **Eventos logados**:
  - `produto_cadastrado` (INFO): ID e nome do produto
  - `validacao_falhou` (WARNING): JSON dos erros de form
  - `produto_save_error` (ERROR): Exceção ao salvar
- **Estrutura**:
  ```json
  {
    "event": "produto_cadastrado",
    "produto_id": 1,
    "produto_nome": "Lápis",
    "request_id": "78037b58-...",
    "trace.id": "4bf92f3577b3..."
  }
  ```

## 📍 Onde Ver Cada Dado em Kibana

| Dado | Localização | Índice |
|-----|------------|--------|
| **Transações HTTP** | Observability → APM → Services → django-app → Transactions | `traces-apm*` |
| **Erros APM** | Observability → APM → Services → django-app → Errors | `logs-apm.error*` |
| **Logs estruturados** | Observability → Logs (ou Discover) | `filebeat-*` |
| **Logs correlacionados** | Dentro de uma transação APM, aba "Logs" | - |
| **CPU/RAM host** | Observability → Infrastructure | `metricbeat-*`, `metrics-apm.internal*` |
| **Uptime/Health Check** | Observability → Uptime | `heartbeat-*` |
| **Métricas de app** | Observability → Metrics | `metrics-apm*` |

## ✅ Verificação Rápida

Confirmar que tudo está funcionando:

```bash
# 1. Stack rodando
docker compose ps

# 2. Django respondendo
curl http://localhost:8000/health/
curl -s http://localhost:8000/ | head -20

# 3. Elasticsearch com dados
curl -u elastic:changeme http://localhost:9200/_cat/indices?v | grep -E "traces-apm|logs-apm|filebeat|metrics-apm|heartbeat"

# 4. Kibana acessível
open http://localhost:5601

# 5. Ver logs estruturados em JSON
tail observability/app-logs/django.log | head -1 | python -m json.tool
```

## 🔍 Cenários Comuns

### Ver requisições lentas
1. Kibana → Observability → APM → Services → django-app → Transactions
2. Ordenar por "Avg. duration" (descendente)
3. Clicar em uma transação
4. Aba "Logs" mostra logs estruturados daquele request

### Correlacionar log com trace
1. Copiar o `request_id` de um log em Kibana → Logs
2. Ir para Kibana → APM → Transactions
3. Filtrar por `http.request.id: <seu_request_id>`
4. Clicar na transação → aba "Logs" mostra o mesmo log

### Monitorar disponibilidade
1. Kibana → Observability → Uptime
2. Ver RTT (Round-Trip Time) e uptime % do health check
3. Configurar alertas com Alerting Rules

### Buscar eventos de negócio
1. Kibana → Discover → `filebeat-*`
2. Filtrar por `event: "produto_cadastrado"` (ou outro evento)
3. Ver: produto_id, produto_nome, request_id, timestamp

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| **Heartbeat mostra Django "down" (connection refused)** | Django deve estar em `0.0.0.0:8000`, não `127.0.0.1`. Use `python manage.py runserver 0.0.0.0:8000` |
| **Django responde 400 ao Heartbeat** | `host.docker.internal` falta em `ALLOWED_HOSTS`. Já está configurado em `core/settings.py` |
| **Sem logs em Kibana** | Verificar permissões de `observability/app-logs` (deve pertencer ao seu usuário). Se criado como root: `docker run --rm -v "$PWD/app-logs:/d" alpine chown $(id -u):$(id -g) /d` |
| **Sem traces no APM** | Executar `curl localhost:8200` (deve responder). Verificar que `setup-apm` completou: `docker compose ps -a \| grep setup-apm` |
| **Elasticsearch não sobe (memory error)** | Aumentar `vm.max_map_count`: `sudo sysctl -w vm.max_map_count=262144` ou ajustar `ES_JAVA_OPTS` em `.env` |
| **Django continua lento apesar de rastreamento** | Desabilitar APM Server se for overhead: `ELASTIC_APM_DISABLE_SEND=true` (logs continuam funcionando) |
| **APM Server fora do ar** | Django continua funcionando normalmente (APM é silencioso) |
| **Muitos logs / disco cheio** | Aumentar `SLOW_REQUEST_THRESHOLD` ou diminuir `LOG_LEVEL=INFO` (não DEBUG) |

## 📚 Arquivos da Integração

| Arquivo | Função |
|---------|--------|
| `core/middleware.py` | Middleware de rastreamento (X-Request-ID, logs de acesso) |
| `core/logging_config.py` | Configuração de logging JSON com injeção de trace IDs |
| `core/views.py` | Endpoint `/health/` para health check e Heartbeat |
| `core/settings.py` | ELASTIC_APM dict, LOGGING config, ALLOWED_HOSTS |
| `.env.example` | Variáveis de ambiente (copiar para `.env`) |
| `requirements.txt` | Dependências: elastic-apm, python-json-logger, python-dotenv, psutil |
| `observability/.env.example` | Config da stack (senha, ELASTIC_PASSWORD) |
| `observability/docker-compose.yml` | Stack: Elasticsearch, Kibana, APM, Filebeat, Metricbeat, Heartbeat |
