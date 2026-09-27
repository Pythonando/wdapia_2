# O que levantar do projeto antes de escrever o cenário

Nada nesta skill assume um projeto. Antes de escrever o `locustfile.py`, os hooks
do seed e o `loadtest.env`, responda a tabela abaixo **lendo o código** — não
suponha. Se algo for ambíguo e mudar o teste, pergunte ao usuário.

| # | Fato | Onde procurar |
| --- | --- | --- |
| 1 | Raiz do repo, `manage.py`, módulo de settings | `manage.py` |
| 2 | Layout de imports (`apps/`, `src/`) | `settings.py` (`sys.path`), imports existentes; se fugir do padrão, `LOADTEST_EXTRA_PYTHONPATH` |
| 3 | Model de usuário e campo de login (`USERNAME_FIELD`) | `AUTH_USER_MODEL`, model |
| 4 | Login: URL, método, nomes dos campos do form, sinal de **sucesso** e de **falha** (302? 200 + `HX-Redirect`? JSON com token?) | `urls.py`, view e template de login |
| 5 | Autenticação: sessão + CSRF, ou token/JWT (DRF)? Nome do cookie CSRF | `settings.py` (`REST_FRAMEWORK`, `CSRF_COOKIE_NAME`) |
| 6 | **Gate de acesso** além de estar logado: paywall/assinatura, e-mail verificado, onboarding, 2FA, permissões | `MIDDLEWARE`, decorators, mixins |
| 7 | Como o app decide que o usuário passa nesse gate (é isso que o seed precisa satisfazer) | código do middleware |
| 8 | Todas as rotas e quais são quentes (home, listagens, detalhes, APIs) | `python3 scripts/list_routes.py` + leitura das views |
| 9 | Métodos aceitos por rota; views que só tratam POST (GET devolve 500) | leitura das views |
| 10 | HTMX (`request.htmx`, django-htmx)? Views que devolvem fragmento | `settings.py`, views |
| 11 | SSE, streaming, WebSocket | grep `StreamingHttpResponse`, `text/event-stream`, `channels` |
| 12 | Rotas com **efeito colateral ou custo**: LLM, e-mail, SMS, cobrança, upload, webhook | grep `openai`, `anthropic`, `stripe`, `send_mail`, `.delay(`, `requests.post` |
| 13 | Variáveis de ambiente obrigatórias p/ o app subir | `settings.py`, `.env.example`, pydantic-settings |
| 14 | Banco (engine, extensões como pgvector/postgis) e imagem Docker equivalente | `DATABASES`, migrations com `CreateExtension` |
| 15 | Redis/Celery/outra fila | `settings.py`, `celery.py` |
| 16 | Nome dos Dockerfiles (web/worker), WORKDIR, entrypoint de produção, porta | raiz do repo, `Procfile`, `railway.toml` |
| 17 | Servidor e config de produção (gunicorn/uvicorn, workers, threads) | entrypoint, `gunicorn.conf.py` |
| 18 | Rota leve e pública para healthcheck | `urls.py` |
| 19 | Models que precisam de dados para listagens/detalhes não virem vazios | models + views de detalhe |
| 20 | Branch principal | `git symbolic-ref refs/remotes/origin/HEAD` (fallback `main`/`master`) |

## Onde cada resposta vai

| Resposta | Arquivo |
| --- | --- |
| 3, 4, 5, 8–12 | `scripts/locustfile.py` |
| 3, 6, 7, 19 | hooks de `scripts/seed_load_test_users.py` |
| 13, 14, 15 | `scripts/loadtest.env` (variáveis do app) |
| 14, 16, 17, 18 | `scripts/loadtest.env` (seção "Ajustes da stack": `LOADTEST_*`, `GUNICORN_*`) |

## Regras que o cenário deve respeitar

1. Só inclua no cenário padrão rotas que respondem corretamente ao método usado.
2. Login: falha de credencial **não** pode contar como sucesso.
3. `name=` estável em toda URL com id.
4. Ids coletados de páginas reais, nunca inventados.
5. Toda task com efeito colateral/custo: tag `expensive` **e** guard
   `if not ALLOW_EXPENSIVE: return`.
6. Rotas de detalhe precisam de dados semeados; senão a lista de ids fica vazia
   e as tasks retornam sem emitir request (relatório "verde" sem medir nada).
