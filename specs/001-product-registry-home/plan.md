# Implementation Plan: Cadastro e Listagem de Produtos na Home

**Branch**: `001-product-registry-home` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-product-registry-home/spec.md`

## Summary

The home page (`/`) has a form to register a product (name and quantity) and, on the same page, a list of every product, newest first. The implementation adds one Django app, `produtos`, to the existing Django 5.2 project. It has a `Produto` model stored in the default SQLite database, a `ModelForm` that holds the validation rules, and a single function view that handles GET and POST. A valid POST uses Post/Redirect/Get so that reloading does not create duplicates, and the messages framework shows the success message. Details are in [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Django 5.2 (already installed in `venv/`). No new packages.

**Storage**: SQLite, the default `db.sqlite3` already set in `core/settings.py` (the user asked to keep it)

**Testing**: Django test runner (`python manage.py test`) with `django.test.TestCase` and the test `Client`

**Target Platform**: Web browser on desktop or phone; the development server is `runserver` on Linux

**Project Type**: Server-rendered web application (a Django monolith)

**Performance Goals**: The home page renders in under 2 s with 1,000 products (SC-005), and a new product appears in under 2 s (SC-002)

**Constraints**: No login; one page; no JavaScript is required; the interface is in pt-BR; the layout must be usable at phone width

**Scale/Scope**: 1 model, 1 form, 1 view, 1 template, 1 URL; up to a few thousand products

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template (only placeholder principles), so it defines no project gates. Instead, the plan was checked against the project conventions in `CLAUDE.md`:

| Check | Status |
|-------|--------|
| New app lives at the repo root next to `core/` and is added to `INSTALLED_APPS` | PASS |
| App URLs are wired into `core/urls.py` with `include()` | PASS |
| Templates are placed in `<app>/templates/` (`APP_DIRS=True`, `DIRS` empty) | PASS |
| Only the built-in test runner is used; no new tooling | PASS |
| No new dependencies (only Django) | PASS |

**Post-design re-check (after Phase 1)**: PASS. The data model, contract and quickstart add nothing beyond the items above. There are no violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-product-registry-home/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R9
├── data-model.md        # Phase 1: Produto entity and validation rules
├── quickstart.md        # Phase 1: setup and validation guide
├── contracts/
│   └── home-page.md     # Phase 1: GET/POST contract for /
├── checklists/
│   └── requirements.md  # From /speckit-specify
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
core/
├── settings.py          # EDIT: add 'produtos' to INSTALLED_APPS; LANGUAGE_CODE='pt-br'; TIME_ZONE='America/Sao_Paulo'
└── urls.py              # EDIT: path('', include('produtos.urls'))

produtos/                # NEW app (python manage.py startapp produtos)
├── __init__.py
├── apps.py
├── admin.py             # register Produto (optional convenience)
├── models.py            # Produto(nome, quantidade, criado_em)
├── forms.py             # ProdutoForm (ModelForm: nome, quantidade)
├── views.py             # home(request): GET lists + blank form; POST validates → save → redirect
├── urls.py              # app_name='produtos'; path('', views.home, name='home')
├── migrations/
│   └── 0001_initial.py
├── templates/
│   └── produtos/
│       └── home.html    # form + messages + list/empty state, inline responsive CSS
└── tests.py             # model, form and view tests covering US1, US2 and edge cases
```

**Structure Decision**: Use a single Django project with one new app, `produtos`, at the repository root, following the layout conventions in `CLAUDE.md`. There is no separate frontend: the page is a server-rendered Django template.

## Complexity Tracking

No constitution violations; nothing to justify.
