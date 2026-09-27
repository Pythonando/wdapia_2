# Research: Cadastro e Listagem de Produtos na Home

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Technical Context had no open NEEDS CLARIFICATION items: the stack is already fixed by the repository (Django 5.2, Python 3.11), and the user asked for the default SQLite database. The decisions below cover the remaining design choices.

## R1. Storage

- **Decision**: Use the default SQLite database that is already configured in `core/settings.py` (`db.sqlite3`).
- **Rationale**: The user explicitly asked for it ("use sqlite padrao mesmo"). The expected volume is a few thousand rows with a single writer, which SQLite handles easily. SC-004 (data survives reloads and restarts) is met because SQLite persists to a file.
- **Alternatives considered**: PostgreSQL was rejected because it adds a service and a dependency with no benefit at this scale.

## R2. App layout

- **Decision**: Create one Django app named `produtos` at the repository root and route it at `''` through `include()` in `core/urls.py`.
- **Rationale**: This follows the convention in CLAUDE.md (new apps go next to `core/` and are wired with `include()`). One app is enough for one entity and one page.
- **Alternatives considered**: Putting the view in `core/` was rejected because `core/` is the project package and should not own models.

## R3. Form handling and validation

- **Decision**: Use a `ModelForm` for `Produto`, with validation declared on the model fields (`max_length=100` for the name; `MinValueValidator(0)` and `MaxValueValidator(1_000_000_000)` for the quantity).
- **Rationale**: Django's form `CharField` has `strip=True` by default. That removes surrounding whitespace, and a whitespace-only name then fails `required` (spec edge case, FR-002). The form `IntegerField` rejects decimals and text (FR-003). A bound form that fails validation re-renders with the user's values and a message next to each invalid field (FR-005).
- **Alternatives considered**: A plain `forms.Form` with manual saving duplicates the model constraints. Client-side-only validation is not enough because the server must refuse invalid data (SC-003).

## R4. Avoid duplicates on reload (FR-009)

- **Decision**: Use Post/Redirect/Get. A valid POST saves the product, adds a success message with `django.contrib.messages`, and returns a 302 redirect to `/`.
- **Rationale**: After the redirect, reloading the page repeats a GET, not the POST, so no duplicate is created. The messages framework (already in `INSTALLED_APPS` and middleware) shows the one-time confirmation that FR-006 requires, and the form is empty on the new GET.
- **Alternatives considered**: Rendering the page directly on a successful POST was rejected because reloading re-submits the form. Tokens to prevent duplicate submits are too complex for this need.

## R5. List ordering and performance

- **Decision**: Add `criado_em = DateTimeField(auto_now_add=True, db_index=True)` and set `Meta.ordering = ['-criado_em', '-id']`. The template renders the whole list with no pagination.
- **Rationale**: This gives newest-first ordering (FR-007). `-id` breaks ties between rows created in the same timestamp. At 1,000 rows, one indexed query and plain server-side rendering stay well under 2 s (SC-005).
- **Alternatives considered**: Ordering by `-id` alone would work, but it does not state the intent, and the spec names the creation time as the sort key. Pagination is out of scope according to the spec's assumptions.

## R6. Safe output (FR-010)

- **Decision**: Rely on Django template autoescaping. Never use `|safe` or `mark_safe` on product data.
- **Rationale**: Autoescaping is on by default and renders names like `<b>x</b>` or `Açúcar & Café` as literal text.
- **Alternatives considered**: None needed.

## R7. Locale

- **Decision**: Set `LANGUAGE_CODE = 'pt-br'` and `TIME_ZONE = 'America/Sao_Paulo'`.
- **Rationale**: The spec assumes a pt-BR interface. With `pt-br`, Django's built-in validation messages (such as "Este campo é obrigatório.") appear in Portuguese without writing custom strings.
- **Alternatives considered**: Hand-writing every error message was rejected because it is more code for the same result.

## R8. Testing

- **Decision**: Use Django's built-in test runner (`python manage.py test`) with `django.test.TestCase` and the test `Client`. Tests live in `produtos/tests.py`.
- **Rationale**: No pytest is set up (CLAUDE.md), and the built-in runner needs no new dependency. Client tests cover every acceptance scenario over real HTTP requests.
- **Alternatives considered**: pytest-django was rejected because it adds a dependency with little gain at this size.

## R9. Styling and mobile use

- **Decision**: Use a single template with a small inline `<style>` block and a `viewport` meta tag. No CSS framework and no static files pipeline.
- **Rationale**: The spec assumes the page must work on desktop and phone browsers. A responsive single-column layout does that without adding `STATICFILES_DIRS` or a CDN dependency.
- **Alternatives considered**: Bootstrap from a CDN was rejected as an unnecessary external dependency for one form and one list.
