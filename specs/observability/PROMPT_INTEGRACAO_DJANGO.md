## Contexto

Projeto Django 6.1 (`core/` = projeto, `usuarios/` = app; rotas em `core/urls.py`, hoje `admin/` e `''`). Roda no host em `localhost:8000` (`python manage.py runserver`), banco SQLite.
A stack de observabilidade já existe em `observability/` (Elasticsearch, Kibana, APM Server, Filebeat, Metricbeat, Heartbeat) e **não deve ser alterada**, exceto se algo abaixo exigir e eu autorizar.

- APM Server: `http://localhost:8200` (o Django roda no host, não em container)
- Usuário Kibana: `elastic`; senha em `observability/.env`
- Filebeat lê arquivos `*.log` do diretório `APP_LOG_DIR` (padrão `observability/app-logs`, montado em `/var/log/app`)
- Heartbeat monitora `APP_HEALTH_URL` (padrão `http://host.docker.internal:8000/`)
- Metricbeat coleta CPU/RAM do host e containers

## Objetivo

Deixar a aplicação 100% integrada: **traces/fluxo de requisição, tempo de resposta, erros, logs estruturados, métricas, disponibilidade e correlação entre logs e traces**.

## Passo a passo a executar

Antes de tudo: use o Context7 para consultar a documentação atual do `elastic-apm` (Django), e leia `core/settings.py`, `core/urls.py`, `usuarios/views.py` e `requirements.txt`. Mostre um plano curto e só então implemente.

### 1. Dependências
- Adicionar ao `requirements.txt` (versões fixadas): `elastic-apm`, `python-json-logger` (ou `structlog`), `python-dotenv` (ou `django-environ`), e `psutil` se necessário.
- Instalar no venv existente (`venv/`).

### 2. Configuração por variáveis de ambiente
- Criar `.env.example` na raiz do projeto (e garantir `.env` no `.gitignore`) com: `ELASTIC_APM_SERVER_URL`, `ELASTIC_APM_SERVICE_NAME`, `ELASTIC_APM_ENVIRONMENT`, `ELASTIC_APM_SECRET_TOKEN` (opcional), `ELASTIC_APM_TRANSACTION_SAMPLE_RATE`, `LOG_DIR`, `LOG_LEVEL`.
- Carregar essas variáveis em `core/settings.py`.
- Sem quebrar o funcionamento local: se o APM Server estiver fora do ar, a aplicação deve continuar subindo normalmente (APM desativado/silencioso, nunca derrubando requests).

### 3. Elastic APM no Django
- Em `settings.py`: adicionar `'elasticapm.contrib.django'` ao `INSTALLED_APPS` e `ELASTIC_APM = {...}` (SERVICE_NAME, SERVER_URL, ENVIRONMENT, `CAPTURE_BODY`, `TRANSACTION_SAMPLE_RATE`, `DJANGO_TRANSACTION_NAME_FROM_ROUTE=True`, `CAPTURE_HEADERS`, `LOG_LEVEL`, `SPAN_FRAMES_MIN_DURATION`, `DISABLE_SEND` controlável por env).
- Adicionar o middleware `elasticapm.contrib.django.middleware.TracingMiddleware` como **primeiro** item de `MIDDLEWARE`.
- Habilitar instrumentação automática de: consultas SQL (SQLite), templates, cache e chamadas HTTP externas (requests/urllib3, se usados).
- Capturar exceções não tratadas com `elasticapm` (handler de logging `elasticapm.contrib.django.handlers.LoggingHandler` para nível ERROR).
- Configurar `SANITIZE_FIELD_NAMES` para nunca enviar senha, token, cookies de sessão, CSRF ou dados pessoais dos formulários de `usuarios`.

### 4. Logs estruturados
- Definir `LOGGING` em `settings.py`:
  - formatter JSON (`python-json-logger`) com `timestamp`, `level`, `logger`, `message`, `module`, `request_id`;
  - handlers: `console` (stdout) e `RotatingFileHandler` em `LOG_DIR/django.log` (criar o diretório automaticamente; apontar `LOG_DIR` por padrão para `observability/app-logs` ou informar como configurar);
  - loggers: `django`, `django.request`, `django.server`, `django.db.backends` (apenas WARNING por padrão), `usuarios` e `core`;
  - injetar `trace.id`, `transaction.id` e `span.id` do Elastic APM em cada log (`elasticapm.handlers.logging.Formatter` / `LoggingFilter`) para permitir a correlação log ↔ trace no Kibana.
- Os logs de erro devem incluir stack trace completo em um único evento (o Filebeat já trata multiline).

### 5. Middleware de request (fluxo + tempo de resposta)
- Criar `core/middleware.py` com um middleware que:
  - gera/propaga `X-Request-ID` (aceita o header de entrada, senão cria UUID) e devolve na resposta;
  - registra um log JSON de acesso por request: método, path, rota nomeada, status, duração em ms, tamanho da resposta, user id (se autenticado), IP, user-agent;
  - adiciona o `request_id` como label customizada na transação APM (`elasticapm.label(request_id=...)`) e o `user.id` via `elasticapm.set_user_context`;
  - loga em nível WARNING respostas lentas (limiar configurável por env, ex.: > 1000 ms) e em ERROR respostas 5xx;
  - adiciona o header `Server-Timing` (opcional).
- Registrar o middleware em `MIDDLEWARE` logo após o `TracingMiddleware`.

### 6. Instrumentação de negócio nas views do app `usuarios`
- Ler `usuarios/views.py` e `usuarios/forms.py`.
- Adicionar spans customizados (`elasticapm.capture_span`) nas operações relevantes (cadastro, login, validações, acessos ao banco importantes).
- Logar eventos de negócio com `logger.info` estruturado (ex.: `usuario_cadastrado`, `login_falhou`) usando `extra={...}` sem dados sensíveis.
- Capturar exceções tratadas que devem aparecer como erro no APM com `elasticapm.get_client().capture_exception()`.

### 7. Health check
- Criar endpoint `GET /health/` (view simples em `core/` ou `usuarios/`, rota em `core/urls.py`) que retorna JSON `{"status": "ok"}` com HTTP 200 e verifica a conexão com o banco (`503` se falhar). Deve ser leve, sem autenticação, e excluído do sampling de traces pesados (`TRANSACTIONS_IGNORE_PATTERNS`).
- Atualizar o valor de `APP_HEALTH_URL` sugerido em `observability/.env.example` para `http://host.docker.internal:8000/health/` (única alteração permitida na pasta `observability/`).
- Configurar `ALLOWED_HOSTS` para aceitar `host.docker.internal` e `localhost` (o Heartbeat chama pelo nome `host.docker.internal`; sem isso o Django responde 400).

### 8. Métricas de aplicação
- Habilitar as métricas de processo do agente APM (`METRICS_INTERVAL`, CPU/RAM do processo Python).
- Opcional: métricas customizadas (contador de cadastros, falhas de login) via `elasticapm.get_client().metrics` ou logs agregáveis.

### 9. Testes
- Adicionar testes em `usuarios/tests.py` / `core/tests.py` para: middleware (header `X-Request-ID` presente, log de acesso emitido), endpoint `/health/` (200 e 503 simulado) e configuração de logging (formato JSON e criação do arquivo).
- Rodar a suíte com `coverage` (o projeto já tem `.coveragerc`) e garantir que passa.

### 10. Verificação ponta a ponta (obrigatória antes de dizer que terminou)
1. Subir a stack: `cd observability && cp .env.example .env && docker compose up -d --build` (ajustar `vm.max_map_count` se necessário).
2. Subir o Django: `python manage.py runserver 0.0.0.0:8000`.
3. Gerar tráfego: acessar `/`, `/admin/`, `/health/`, uma rota inexistente (404) e forçar um erro 500 controlado (sem deixar código de teste no projeto).
4. Confirmar no Elasticsearch/Kibana que existem dados em: `traces-apm*` (transações e spans), `logs-apm.error*` (erros), `filebeat-*` (logs JSON com `trace.id`), `metrics-apm*` / `metricbeat-*` (CPU/RAM) e `heartbeat-*` (uptime e RTT). Usar `curl -u elastic:$ELASTIC_PASSWORD localhost:9200/_cat/indices?v` e as APIs do Kibana.
5. Verificar que clicar em uma transação no APM mostra os logs correlacionados.
6. Reportar o que foi validado e o que falhou, com a saída dos comandos.

### 11. Documentação
- Criar `observability/README.md` (ou seção no README do projeto) com: como subir a stack, variáveis de ambiente, como acessar o Kibana, onde ver cada tipo de dado (APM → Services, Observability → Logs, Infrastructure, Uptime/Synthetics) e troubleshooting comum.

## Restrições
- Não commitar segredos; `.env` fora do git.
- Não alterar modelos, migrações ou regras de negócio existentes.
- Manter o estilo do código existente e mudanças mínimas nas views.
- Se algum passo depender de decisão minha (ex.: nível de detalhe dos logs, limiar de lentidão, captura de body), pergunte antes de implementar.
- Ao final, faça um resumo dos arquivos criados/alterados. Só faça commit se eu pedir.
