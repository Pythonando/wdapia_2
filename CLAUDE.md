# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Django 5.2 on Python 3.11, with a local virtualenv in `venv/` (not `.venv`). No `requirements.txt` exists yet; installed packages are only Django and its dependencies (`asgiref`, `sqlparse`).
- Activate the venv directly instead of prefixing commands: `source venv/bin/activate`.

## Commands

```bash
source venv/bin/activate
python manage.py runserver            # dev server at http://127.0.0.1:8000
python manage.py makemigrations       # after model changes
python manage.py migrate
python manage.py startapp <name>      # then add it to INSTALLED_APPS in core/settings.py
python manage.py test                 # all tests
python manage.py test <app>.tests.<TestCase>.<test_method>   # a single test
```

There's no linter, formatter, or pytest setup configured.

## Architecture

- `core/` is the project package. It holds `settings.py`, the root `urls.py` (routes `admin/` and includes `produtos.urls` at `''`), and `wsgi.py`/`asgi.py`.
- `produtos/` is the only app. It serves the home page (`produtos:home`, URL `/`): a single function view `home` with a `ProdutoForm` (ModelForm) to register a `Produto` (nome, quantidade, criado_em) and a newest-first list on the same page. A valid POST saves, adds a `messages.success`, and redirects back to `/` (Post/Redirect/Get). Validation rules live on the model fields, and the form applies them. Tests are in `produtos/tests.py`. Specs for the feature are in `specs/001-product-registry-home/`.
- New apps belong at the repository root next to `core/`, and their URLs are wired in with `include()` in `core/urls.py`.
- Templates: `TEMPLATES['DIRS']` is empty and `APP_DIRS=True`, so templates currently resolve only from `<app>/templates/`. Static files: only `STATIC_URL` is set, with no `STATICFILES_DIRS` or `STATIC_ROOT`.
- Database: SQLite at `db.sqlite3` (the default, kept on purpose). Migrations have been applied.
- The settings are the development defaults: a hardcoded `SECRET_KEY`, `DEBUG=True`, and empty `ALLOWED_HOSTS`. The locale is pt-BR: `LANGUAGE_CODE='pt-br'` and `TIME_ZONE='America/Sao_Paulo'`, so Django's built-in validation messages appear in Portuguese.

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
