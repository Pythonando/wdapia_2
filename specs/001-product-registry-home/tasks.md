---

description: "Task list for Cadastro e Listagem de Produtos na Home"
---

# Tasks: Cadastro e Listagem de Produtos na Home

**Input**: Design documents from `/specs/001-product-registry-home/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/home-page.md, quickstart.md

**Tests**: Included. The plan lists `produtos/tests.py` in the source tree, and quickstart.md expects `python manage.py test produtos` to cover the US1 and US2 acceptance scenarios and the edge cases. Tests use Django's built-in runner (`django.test.TestCase` + `self.client`). There is no pytest.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story the task belongs to (US1, US2)
- Paths are relative to the repository root (the Django project, next to `core/`)

## Environment

Run every command after `source venv/bin/activate` from the repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the app and configure the project

- [X] T001 Run `python manage.py startapp produtos` at the repository root, creating `produtos/` with `__init__.py`, `apps.py`, `admin.py`, `models.py`, `views.py`, `tests.py` and `migrations/`
- [X] T002 Edit `core/settings.py`: append `'produtos'` to `INSTALLED_APPS`, set `LANGUAGE_CODE = 'pt-br'`, and set `TIME_ZONE = 'America/Sao_Paulo'`. Leave `DATABASES` untouched: it stays on the default SQLite `BASE_DIR / 'db.sqlite3'`, as the user asked (research R1, R7)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The model, migration, route and page skeleton that both stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Define `Produto` in `produtos/models.py` per data-model.md:
  - `nome = models.CharField('nome', max_length=100)`: "max 100 chars", required, no unique constraint ("Duplicates are allowed")
  - `quantidade = models.PositiveIntegerField('quantidade', validators=[MinValueValidator(0), MaxValueValidator(1_000_000_000)])`: "`0 ≤ quantidade ≤ 1_000_000_000`"
  - `criado_em = models.DateTimeField('criado em', auto_now_add=True, db_index=True)`
  - `Meta`: `ordering = ['-criado_em', '-id']`, `verbose_name = 'produto'`, `verbose_name_plural = 'produtos'`
  - `__str__` returns `f'{self.nome} ({self.quantidade})'`
- [X] T004 Run `python manage.py makemigrations produtos` to create `produtos/migrations/0001_initial.py`, then `python manage.py migrate`, which also applies the pending `django.contrib` migrations
- [X] T005 [P] Register `Produto` in `produtos/admin.py` with `@admin.register(Produto)`, `list_display = ('nome', 'quantidade', 'criado_em')`
- [X] T006 [P] Create `produtos/urls.py` with `app_name = 'produtos'` and `urlpatterns = [path('', views.home, name='home')]`, and add `path('', include('produtos.urls'))` to `core/urls.py`, importing `include` from `django.urls`. Keep the existing `admin/` route
- [X] T007 Create a minimal `home(request)` view in `produtos/views.py`, decorated with `@require_http_methods(['GET', 'POST'])` (contract: other methods → 405). For now it only does `return render(request, 'produtos/home.html', {})`
- [X] T008 Create the page skeleton in `produtos/templates/produtos/home.html`:
  - `<!doctype html>`, `<html lang="pt-br">`, `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">`, `<title>Produtos</title>`, `<h1>Produtos</h1>`
  - an inline `<style>` with one centered column (`max-width: 640px; margin: 0 auto; padding: 16px`) and inputs at `width: 100%`, so there is no horizontal scroll at 375px (research R9)
  - a messages block that renders `{% for message in messages %}<p class="msg msg-{{ message.tags }}">{{ message }}</p>{% endfor %}`
  - empty sections marked `<!-- formulário -->` and `<!-- lista -->` for US1 and US2 to fill
  - Never use `|safe` (FR-010)

**Checkpoint**: `python manage.py runserver` → GET `/` returns 200 with the heading. The foundation is ready.

---

## Phase 3: User Story 1 - Cadastrar um produto pela home (Priority: P1) 🎯 MVP

**Goal**: The user submits a name and a quantity on `/`. Valid data is saved and redirected back to `/` with a success message. Invalid data is refused with messages next to the fields, and the typed values stay in the form.

**Independent Test**: POST `nome=Caneta&quantidade=10` to `/` → 302 to `/`, one `Produto` exists in the database, and following the redirect shows "Produto cadastrado com sucesso." and an empty form.

### Tests for User Story 1

- [X] T009 [P] [US1] In `produtos/tests.py`, add `class CadastroProdutoTests(TestCase)` using `self.client` and `reverse('produtos:home')`:
  - valid POST `Caneta`/`10` → status 302, `Location` is `/`, `Produto.objects.count() == 1`, and the saved `nome == 'Caneta'`, `quantidade == 10`
  - valid POST with `follow=True` → the response contains "Produto cadastrado com sucesso.", and the `nome` input has no `value="Caneta"`
  - `nome='   '` → status 200, count 0, error on the `nome` field (`response.context['form'].errors` has `'nome'`)
  - `nome='  Lápis  '` → saved as `'Lápis'` (stripped)
  - a 101-char `nome` → rejected; a 100-char `nome` → accepted
  - `quantidade` values `''`, `'-1'`, `'2.5'`, `'abc'`, `'1000000001'` → each rejected, with the error on `quantidade`; `'0'` and `'1000000000'` → accepted
  - after an invalid POST (`nome='Borracha'`, `quantidade='-1'`), the response HTML contains `value="Borracha"` (values kept, US1-4)
  - two POSTs of `Caneta`/`10` → count 2 (duplicates allowed)
  - a PUT to `/` → 405

### Implementation for User Story 1

- [X] T010 [P] [US1] Create `produtos/forms.py` with `class ProdutoForm(forms.ModelForm)`: `Meta.model = Produto`, `fields = ['nome', 'quantidade']`, and `widgets` that set `nome` to `TextInput(attrs={'maxlength': 100, 'autofocus': True})` and `quantidade` to `NumberInput(attrs={'min': 0, 'max': 1000000000, 'step': 1})`. The ModelForm `CharField` already strips whitespace (`strip=True`), so a whitespace-only name fails `required`. The model validators enforce the "`0 ≤ quantidade ≤ 1_000_000_000`" range (research R3)
- [X] T011 [US1] Extend `home` in `produtos/views.py` to use Post/Redirect/Get (research R4). On POST, bind `ProdutoForm(request.POST)`. If it is valid, `form.save()`, call `messages.success(request, 'Produto cadastrado com sucesso.')` and `return redirect('produtos:home')`. If it is invalid, fall through and re-render with the bound form. On GET, use `ProdutoForm()`. Pass `{'form': form}` to `produtos/home.html`
- [X] T012 [US1] Fill the `<!-- formulário -->` section of `produtos/templates/produtos/home.html` with `<form method="post" action="{% url 'produtos:home' %}">`, `{% csrf_token %}`, and for each of `form.nome` and `form.quantidade` a `<label>`, the field, and its `{{ field.errors }}` right below it. Also render `{{ form.non_field_errors }}` and `<button type="submit">Cadastrar</button>`

**Checkpoint**: `python manage.py test produtos.tests.CadastroProdutoTests` passes. US1 works on its own: products are saved and can be checked in `/admin/` or the shell.

---

## Phase 4: User Story 2 - Ver os produtos cadastrados na mesma página (Priority: P1)

**Goal**: `/` lists every product (name and quantity), newest first, below the form, and shows an empty-state message when there are none.

**Independent Test**: Create products with `Produto.objects.create(...)` and GET `/` → all of them appear in newest-first order. With no products, GET `/` shows "Nenhum produto cadastrado ainda."

### Tests for User Story 2

- [X] T013 [US2] In `produtos/tests.py` (same file as T009, so do this after it), add `class ListagemProdutoTests(TestCase)`:
  - empty database → GET `/` status 200, contains "Nenhum produto cadastrado ainda."
  - create `Caneta`/`10` and then `Lápis`/`0` with `Produto.objects.create` → the response contains both names and quantities, and `Lápis` appears before `Caneta` in `response.content.decode()` (newest first, FR-007)
  - two products created in the same `criado_em` (set it explicitly with `.update()`) → the one with the higher `id` comes first (the `-id` tie-breaker)
  - after a successful POST followed by the redirect, the new product is in the list at the top (US2-2)
  - a product named `<b>x</b>` → the response contains `&lt;b&gt;x&lt;/b&gt;` and does not contain `<b>x</b>` (FR-010); `Açúcar & Café` renders as `Açúcar &amp; Café`
  - with 1,000 products created via `bulk_create`, GET `/` runs in `self.assertNumQueries(...)` with a constant number of queries (the list is a single query; no N+1), for SC-005

### Implementation for User Story 2

- [X] T014 [US2] In `produtos/views.py`, add `'produtos': Produto.objects.all()` to the context in `home` (the default ordering `['-criado_em', '-id']` applies), for both GET and the invalid-POST re-render (the contract says the list still appears after a validation error)
- [X] T015 [US2] Fill the `<!-- lista -->` section of `produtos/templates/produtos/home.html`: `<h2>Produtos cadastrados</h2>`, then `{% for produto in produtos %}` rendering `<li><span class="nome">{{ produto.nome }}</span> <span class="qtd">{{ produto.quantidade }}</span></li>` inside a `<ul>`, and `{% empty %}<p>Nenhum produto cadastrado ainda.</p>`. Add CSS so each `<li>` is a row with the name on the left and the quantity on the right (`display: flex; justify-content: space-between`), and long names wrap (`overflow-wrap: anywhere`)

**Checkpoint**: `python manage.py test produtos` passes. Both stories work together on `/`.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T016 Run the full suite with `python manage.py test` and confirm 0 failures
- [X] T017 Follow every step of `specs/001-product-registry-home/quickstart.md`: the 10 manual checks with `runserver`, including restart persistence and the 375px width check, and the curl check that the server itself rejects an invalid quantity
- [X] T018 [P] Update `CLAUDE.md` (Architecture and Environment sections): the `produtos` app now exists and is routed at `''`, `LANGUAGE_CODE='pt-br'` and `TIME_ZONE='America/Sao_Paulo'`, and migrations have been applied to `db.sqlite3`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 → T002
- **Foundational (Phase 2)**: needs Setup. T003 → T004. T005 needs T003. T006, T007 and T008 need T001 only. T007 must exist before T006 is imported at runtime
- **US1 (Phase 3)**: needs Phase 2
- **US2 (Phase 4)**: needs Phase 2. It does not need US1: its tests create data through the ORM. The only shared files are `produtos/views.py`, `home.html` and `tests.py`, so on a single machine the edits run one after another
- **Polish (Phase 5)**: needs US1 and US2

### Within Each Story

- Write the tests first and watch them fail (T009 before T011 and T012; T013 before T014 and T015)
- Form (T010) → view (T011) → template (T012)

### Parallel Opportunities

- Phase 2: T005, T006 and T008 touch different files and can run together once T001 is done (and T005 once T003 is done)
- US1: T009 (`tests.py`) and T010 (`forms.py`) run in parallel
- Across stories: US2's T014/T015 could be developed in parallel with US1 by a second person, but they edit the same `views.py` and `home.html`, so merge carefully
- T018 (docs) can run alongside T016 and T017

---

## Parallel Example: User Story 1

```bash
Task: "Write CadastroProdutoTests in produtos/tests.py"          # T009
Task: "Create ProdutoForm in produtos/forms.py"                  # T010
# then, one after another:
Task: "Add POST/PRG handling to home in produtos/views.py"      # T011
Task: "Render the form in produtos/templates/produtos/home.html" # T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 → Phase 2 → Phase 3
2. **STOP and VALIDATE**: `python manage.py test produtos.tests.CadastroProdutoTests`, then submit a product in the browser and check that it shows in `/admin/`

### Incremental Delivery

1. Setup + Foundational → `/` returns the page skeleton
2. US1 → registering works (MVP)
3. US2 → the list appears on the same page, which completes the requested feature
4. Polish → full suite, quickstart checks, docs

---

## Notes

- Keep validation in the model and the ModelForm only. Do not duplicate the rules in the view
- Never mark product data safe in templates
- Commit after each phase checkpoint
