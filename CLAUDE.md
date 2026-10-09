# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Django 5.2 on Python 3.11, with a local virtualenv in `venv/` (not `.venv`).
- Activate the venv directly instead of prefixing commands: `source venv/bin/activate`.
- `requirements.txt` exists and is **curated**: it lists only direct dependencies with pinned versions. Never overwrite it with `pip freeze` (the `venv/` also holds dev-only tooling that must not reach production); add new packages by hand with the installed version.

  | Package | Why it is there |
  | --- | --- |
  | `Django`, `asgiref`, `sqlparse` | The framework and its dependencies. |
  | `python-decouple` | `config()` in `core/settings.py` reads `SECRET_KEY`, `DEBUG` and the `PG*` variables. |
  | `python-dotenv` | `load_dotenv()` in `core/settings.py` loads `.env` for the variables read with `os.getenv` (logging, Elastic APM, slow-request threshold). |
  | `gunicorn` | Production WSGI server (see `Procfile`). |
  | `whitenoise` | Serves static files from the Django process in production. |
  | `psycopg2-binary` | Postgres driver, used when `DEBUG=False`. |
  | `elastic-apm` | APM agent: an installed app, a middleware and a logging handler. |
  | `python-json-logger` | JSON log formatter used by `core/logging_config.py`. |
  | `coverage` | Test coverage (configured in `.coveragerc`). |
  | `psutil` | Listed, but not imported by the project's own code. |

- A `.env` file at the repository root is **required**: `SECRET_KEY` has no default, so without it (or an exported `SECRET_KEY` variable) every `manage.py` command fails with decouple's `UndefinedValueError`. `.env` is git-ignored; copy `.env.example` and fill in the values. Generate a key with `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`.

### Environment variables

Two readers coexist in `core/settings.py`: `decouple.config()` (for `SECRET_KEY`, `DEBUG`, `PG*`) and `load_dotenv()` + `os.getenv` (for everything else). Both read the same `.env`, and a real environment variable wins over the file in both.

| Variable | Read with | Default | Purpose |
| --- | --- | --- | --- |
| `SECRET_KEY` | `config` | none (required) | Django secret key. Use a different value in production. |
| `DEBUG` | `config` (cast to bool) | `False` | Switches the database and the static files storage (see Architecture). Local `.env` sets `True`. |
| `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT` | `config` | none (required when `DEBUG=False`) | Postgres connection. Not read at all when `DEBUG=True`, so keep them out of the local `.env`. |
| `LOG_DIR` | `os.getenv` | `observability/app-logs` under the repo root | Where `django.log` and `error.log` are written. The directory is created on startup. |
| `LOG_LEVEL` | `os.getenv` | `DEBUG` | Level for the console and file log handlers. |
| `SLOW_REQUEST_THRESHOLD` | `os.getenv` | `1000` | Milliseconds above which a request is logged as `slow_request`. |
| `ELASTIC_APM_SERVER_URL` | `os.getenv` | `http://localhost:8200` | APM server address. |
| `ELASTIC_APM_SERVICE_NAME` | `os.getenv` | `django-app` | Service name shown in APM. |
| `ELASTIC_APM_ENVIRONMENT` | `os.getenv` | `development` | Environment label in APM. |
| `ELASTIC_APM_SECRET_TOKEN` | `os.getenv` | empty | APM server token. |
| `ELASTIC_APM_TRANSACTION_SAMPLE_RATE` | `os.getenv` | `1.0` | Fraction of transactions sampled. |
| `APP_HEALTH_URL` | not read by Django | — | Used only by the heartbeat container in `observability/docker-compose.yml`. |
| `PORT` | not read by Django | — | Injected by Railway and used by the `Procfile` for the gunicorn bind. |

## Commands

```bash
source venv/bin/activate
pip install -r requirements.txt       # install the pinned dependencies
cp .env.example .env                  # first time only; then set SECRET_KEY (DEBUG=True for local work)
python manage.py runserver            # dev server at http://127.0.0.1:8000
python manage.py makemigrations       # after model changes
python manage.py migrate
python manage.py startapp <name>      # then add it to INSTALLED_APPS in core/settings.py
python manage.py test                 # all tests
python manage.py test <app>.tests.<TestCase>.<test_method>   # a single test
python manage.py collectstatic --noinput   # copies static files into staticfiles/ (git-ignored)
```

To check the production path locally without a database connection:

```bash
DEBUG=False SECRET_KEY=x PGDATABASE=x PGUSER=x PGPASSWORD=x PGHOST=x PGPORT=5432 \
  python manage.py check --deploy
gunicorn core.wsgi --check-config
```

There's no linter, formatter, or pytest setup configured.

## Architecture

- `core/` is the project package. It holds `settings.py`, the root `urls.py` (routes `health/`, `admin/` and includes `produtos.urls` at `''`), and `wsgi.py`/`asgi.py`. It also has its own code:
  - `core/views.py`: `health_check` (URL `/health/`, name `health`, GET only). It runs `SELECT 1` and returns `{"status": "ok"}` with 200, or `{"status": "error", "detail": ...}` with 503 when the database is unreachable.
  - `core/middleware.py`: `RequestTrackingMiddleware`. It gives every request an ID (reusing an incoming `X-Request-ID` header), logs one JSON line per request to the `core` logger (`request_ok`, `slow_request` above `SLOW_REQUEST_THRESHOLD`, or `request_error` for 5xx), labels the APM transaction, and adds the `X-Request-ID` and `Server-Timing` response headers.
  - `core/logging_config.py`: `get_logging_config()` builds `LOGGING` with a console handler, rotating JSON files (`django.log`, `error.log`, 10 MB with 5 backups) in `LOG_DIR`, and an Elastic APM handler for errors.
  - `core/tests.py`: tests for the middleware, the health check and the logging configuration.
- Middleware order in `core/settings.py` matters: `elasticapm` `TracingMiddleware`, then `core.middleware.RequestTrackingMiddleware`, then `SecurityMiddleware`, then `whitenoise.middleware.WhiteNoiseMiddleware` (it must stay immediately after `SecurityMiddleware`), then Django's defaults.
- `observability/` holds a local Elastic stack (`docker-compose.yml` with Elasticsearch, Kibana, APM server, Filebeat, Heartbeat and Metricbeat) that consumes the app's logs and APM data; see `observability/README.md`. It is not part of the Railway deploy.
- `produtos/` is the only app. It serves the home page (`produtos:home`, URL `/`): a single function view `home` with a `ProdutoForm` (ModelForm) to register a `Produto` (nome, quantidade, criado_em) and a newest-first list on the same page. A valid POST saves, adds a `messages.success`, and redirects back to `/` (Post/Redirect/Get). Validation rules live on the model fields, and the form applies them. Tests are in `produtos/tests.py`. Specs for the feature are in `specs/001-product-registry-home/`.
- New apps belong at the repository root next to `core/`, and their URLs are wired in with `include()` in `core/urls.py`.
- Templates: `TEMPLATES['DIRS']` is empty and `APP_DIRS=True`, so templates currently resolve only from `<app>/templates/`. 
- Static files: `STATIC_URL='static/'` and `STATIC_ROOT=BASE_DIR / 'staticfiles'` (the `collectstatic` target, git-ignored); there is no `STATICFILES_DIRS`. `STORAGES['staticfiles']` depends on `DEBUG`: Django's plain `StaticFilesStorage` when `DEBUG=True`, and `whitenoise.storage.CompressedManifestStaticFilesStorage` when `DEBUG=False`. The manifest storage is kept out of development and tests on purpose, because it makes every `{% static %}` fail until `collectstatic` has run.
- Database: chosen by `DEBUG` in `core/settings.py`. With `DEBUG=True` it is SQLite at `db.sqlite3`; with `DEBUG=False` it is Postgres, configured from `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST` and `PGPORT`, with `CONN_MAX_AGE=600` and a `connect_timeout` of 10 seconds.
- `DEBUG` is therefore the single switch between the development and production setups. It defaults to `False`, so an environment that forgets to set it gets the production setup and fails at startup if the `PG*` variables are missing.
- Hosts: `ALLOWED_HOSTS` is `localhost`, `127.0.0.1`, `host.docker.internal` and `.railway.app`; `CSRF_TRUSTED_ORIGINS` is `https://*.railway.app`. A custom domain has to be added to both.
- The locale is pt-BR: `LANGUAGE_CODE='pt-br'` and `TIME_ZONE='America/Sao_Paulo'`, so Django's built-in validation messages appear in Portuguese.

## Deployment (Railway)

The project is prepared to run on Railway. Locally it behaves as before (SQLite, `runserver`); on Railway the same code runs behind gunicorn, talks to Postgres and serves its own static files through WhiteNoise. The procedure that produced this setup is the skill [`.claude/skills/django-deploy`](.claude/skills/django-deploy/SKILL.md); follow it when repeating or extending the deploy configuration.

- `Procfile` defines the start command, which runs on every start of the service:

  ```procfile
  web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn core.wsgi --bind 0.0.0.0:$PORT
  ```

  The steps are chained with `&&`, so a failed migration or `collectstatic` stops the service from starting.
- Variables to set on the Railway app service:

  | Variable | Value |
  | --- | --- |
  | `DEBUG` | `False` |
  | `SECRET_KEY` | A production key, different from the local one. |
  | `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT` | References to the Railway Postgres service, for example `PGHOST=${{Postgres.PGHOST}}`. |

Known gaps and gotchas (not handled in the code yet):

- No HTTPS hardening settings exist (`SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`), so `check --deploy` reports security warnings.
- The Elastic APM agent is always enabled and `ELASTIC_APM_SERVER_URL` defaults to `http://localhost:8200`. On Railway there is no APM server at that address unless the variable is set to a reachable one.
- Logs are also written to files under `LOG_DIR` (inside the container on Railway). Only the console handler output reaches the Railway log viewer.
- The Python version is not pinned for the platform: there is no `runtime.txt`, `.python-version`, `railway.json` or `nixpacks.toml`.
- The old hardcoded `django-insecure-...` `SECRET_KEY` was removed from `core/settings.py` but remains in the git history. Never reuse it.
- `.github/workflows/` contains only Claude Code workflows; nothing runs the test suite or deploys automatically from CI.

## TDD workflow (mandatory for every new feature)

Para cada nova funcionalidade, siga obrigatoriamente a skill

[`.claude/skills/django-tdd`](.claude/skills/django-tdd) — escreva os testes **antes** da

implementação (Red → Green → Refactor).

Cobertura mínima exigida por funcionalidade:

- **Models** — campos, validações, métodos, `__str__`, constraints.
- **Forms** — validação de campos, `clean_*`, mensagens de erro.
- **Views** — status codes, contexto, permissões, redirecionamentos.
- **Templates** — renderização, blocos, presença de elementos esperados.
- **Integração** — fluxo end-to-end cobrindo a jornada do usuário.

Só marque a funcionalidade como concluída depois que todos esses níveis de testes estiverem
verdes.

## ⚠️ OBRIGATÓRIO: Sincronização de documentação
**Ao finalizar QUALQUER alteração de código neste repositório, é OBRIGATÓRIO executar,
como última etapa, o agente `doc-sync-onboarding` para atualizar a documentação
(`CLAUDE.md` e arquivos em `docs/`) refletindo as mudanças feitas.**
Isso vale para toda e qualquer modificação: novos modelos/campos, migrations, views, rotas,
tasks assíncronas, signals, middlewares, integrações, variáveis de ambiente, scripts de
infraestrutura, etc. Nenhuma tarefa de código é considerada concluída antes de a
documentação ter sido sincronizada por esse agente.


# 🤖 Orquestração de agentes (quem faz o quê)


O trabalho é dividido entre papéis, cada um com o modelo mais adequado à complexidade da tarefa. Ao delegar via `Agent`, escolha o papel pelo tipo de tarefa e passe o `model` correspondente.


### 1) Tech-lead e Desenvolvedor — modelo mais poderoso (`fable` ou `opus`)


Use para tudo que exige decisão, raciocínio ou código de produção.


- Decide **quais agentes executarão cada tarefa** e delega o restante aos papéis abaixo.
- Escreve as **specs** (`speckit-specify`, `speckit-plan`, `speckit-tasks`) e as decisões de arquitetura.
- **Implementa o código** de negócio: models, migrations, views, tasks Celery, integrações, pagamentos, segurança, performance.
- Revisa o resultado dos demais agentes antes de considerar a tarefa concluída.


### 2) Escritor de testes — modelo intermediário (`sonnet`)


- Escreve **todos os tipos de teste**: unitários, integração, e2e, de regressão, etc. (`pytest`, `pytest-django`, `factory_boy`; ver skill `django-tdd`).
- Recebe do tech-lead a spec/comportamento esperado e devolve testes executáveis; não altera código de produção (se achar um bug, reporta ao tech-lead).


### 3) Redator — modelo mais simples (`haiku`, o de menor custo)


Tarefas de texto e ajustes triviais:


- Escrever **mensagens de commit** (seguindo a atribuição definida nas instruções de commit).
- Escrever/atualizar **tasks no Linear**.
- Criar **changelogs**.
- Corrigir **falhas banais de interface** (typos, textos, espaçamento, classes Tailwind simples).


### 4) Dev júnior — `haiku`


Tarefas **não críticas e de baixa complexidade**:


- **Iniciar projetos** (setup inicial, `uv sync`, `.env`, migrations locais).
- **Rodar containers** (`docker build`/`run`, subir stack, Redis, worker Celery).
- Corrigir falhas de interface simples.
- Qualquer outra tarefa rotineira de baixo risco. Se a tarefa se revelar crítica ou complexa, devolve ao tech-lead.


### Regras gerais de delegação


- Em caso de dúvida sobre a complexidade, **suba um nível** de modelo em vez de descer.
- Código que toca pagamentos (`payments`), autenticação/assinaturas (`accounts`), segurança ou migrations de dados é **sempre** do tech-lead/desenvolvedor.
- A sincronização de documentação (`doc-sync-onboarding`) continua obrigatória como última etapa de qualquer alteração de código (ver seção acima).
