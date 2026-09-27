# Data Model: Cadastro e Listagem de Produtos na Home

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

## Entity: Produto

Table: `produtos_produto` (Django app `produtos`, SQLite `db.sqlite3`).

| Field | Type | Constraints | Source |
|-------|------|-------------|--------|
| `id` | auto primary key (`BigAutoField`, the project default) | Generated automatically | Django default |
| `nome` | text, max 100 chars | Required. Surrounding whitespace is stripped by the form, and the value must not be blank after stripping. Duplicates are allowed (no unique constraint). | FR-002, edge cases |
| `quantidade` | non-negative integer | Required, whole number, `0 ≤ quantidade ≤ 1_000_000_000` | FR-003, edge cases |
| `criado_em` | datetime | Set automatically on insert (`auto_now_add`) and indexed. Users never edit it. | FR-007 |

**Default ordering**: `-criado_em`, then `-id` (newest first, stable).

**String representation**: `"{nome} ({quantidade})"`, for the admin and debugging.

## Validation rules

| Input | Result | Message field |
|-------|--------|---------------|
| `nome` empty or whitespace-only | rejected | `nome` (required) |
| `nome` longer than 100 chars after stripping | rejected | `nome` (max length) |
| `quantidade` empty | rejected | `quantidade` (required) |
| `quantidade` not an integer (`"2.5"`, `"abc"`) | rejected | `quantidade` (invalid number) |
| `quantidade` < 0 | rejected | `quantidade` (min value) |
| `quantidade` > 1,000,000,000 | rejected | `quantidade` (max value) |
| `nome` with accents or symbols (`Açúcar & Café`, `<b>x</b>`) | accepted, stored as typed, and displayed escaped | — |

The model fields define the validation, and the `ModelForm` applies it, so the database and the form share one set of rules.

## Relationships

None. `Produto` stands alone and has no owner or user link (there is no login, per the spec's assumptions).

## State transitions

None. A product is created and then only read. Editing and deleting are out of scope.

## Migration

`produtos/migrations/0001_initial.py` creates the table and the index on `criado_em`. The first `migrate` also applies the pending `django.contrib` migrations, because the database has never been migrated.
