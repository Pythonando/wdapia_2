# UI/HTTP Contract: Home (`/`)

A single URL serves both the form and the list. The URL name is `produtos:home`.

## GET `/`

**Response**: `200 OK`, HTML (`text/html; charset=utf-8`), `lang="pt-br"`.

The page contains:

1. **Flash message area**: shows the one-time success message ("Produto cadastrado com sucesso.") after a successful POST, and nothing otherwise.
2. **Form** (`method="post"`, `action="/"`, with the CSRF token):
   - `nome`: text input, `maxlength="100"`, `required`
   - `quantidade`: number input, `min="0"`, `max="1000000000"`, `step="1"`, `required`
   - a submit button labeled "Cadastrar"
   - The inputs start empty.
3. **List of products**: every `Produto`, newest first. Each item shows the `nome` (escaped) and the `quantidade`.
4. **Empty state**: when there are no products, the message "Nenhum produto cadastrado ainda." replaces the list.

Browser attributes (`required`, `min`, `max`) help the user, but the server still validates every rule (see POST).

## POST `/`

**Request body** (`application/x-www-form-urlencoded`):

| Field | Required | Rules |
|-------|----------|-------|
| `csrfmiddlewaretoken` | yes | Django CSRF token |
| `nome` | yes | 1–100 chars after strip |
| `quantidade` | yes | integer, 0 to 1,000,000,000 |

**Valid input** → the server saves one `Produto` and responds `302 Found` with `Location: /`. The success message is queued for the next GET, so reloading after the redirect does not create a second product (FR-009).

**Invalid input** → no product is saved. The response is `200 OK` with the same page, where:
- the form is re-rendered with the values the user submitted
- each invalid field shows its error message in Portuguese next to the field
- the product list still appears below the form

**Missing or invalid CSRF token** → `403 Forbidden` (Django default).

## Other methods

Methods other than GET and POST → `405 Method Not Allowed`.
