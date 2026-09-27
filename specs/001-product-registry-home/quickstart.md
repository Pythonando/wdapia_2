# Quickstart: Cadastro e Listagem de Produtos na Home

Use this guide to check that the feature works end to end. For details, see [data-model.md](./data-model.md) and [contracts/home-page.md](./contracts/home-page.md).

## Prerequisites

- Python 3.11 venv at `venv/` with Django 5.2 (already present)
- Run everything from the repository root

## Setup

```bash
source venv/bin/activate
python manage.py makemigrations produtos
python manage.py migrate
```

Expected: the migration `produtos/migrations/0001_initial.py` is created, and `migrate` applies it along with the `django.contrib` migrations.

## Automated validation

```bash
python manage.py test produtos
```

Expected: all tests pass. They cover the acceptance scenarios for US1 and US2 and the edge cases in the spec.

## Manual validation

Start the server with `python manage.py runserver` and open http://127.0.0.1:8000/.

| # | Action | Expected result | Spec |
|---|--------|-----------------|------|
| 1 | Open the home page on an empty database | Form visible, and the text "Nenhum produto cadastrado ainda." | US2-3, FR-008 |
| 2 | Submit `Caneta` / `10` | Redirected back to the home page with the message "Produto cadastrado com sucesso.", an empty form, and "Caneta — 10" at the top of the list | US1-1, US2-2, FR-006 |
| 3 | Press F5 right after step 2 | No new product; the list still has 1 item | FR-009 |
| 4 | Submit `Lápis` / `0` | Accepted; "Lápis" is shown above "Caneta" | Edge case (zero), FR-007 |
| 5 | Submit a name of only spaces with `5` | Rejected; error on `nome`; the `5` stays in the field | US1-2, US1-4 |
| 6 | Submit `Borracha` with `-1`, `2.5`, then `1000000001` (remove browser validation with devtools, or use curl) | Each one is rejected with an error on `quantidade`, and `Borracha` stays in the field | US1-3, US1-4 |
| 7 | Submit `Açúcar & Café` / `3`, then `<b>x</b>` / `1` | Both appear exactly as typed; the second one is not bold | FR-010 |
| 8 | Submit `Caneta` / `10` again | Accepted as a separate item | Edge case (duplicates) |
| 9 | Stop and restart `runserver`, then reload | All products are still listed | FR-004, SC-004 |
| 10 | Open the page at phone width (devtools, 375px) | Form and list are usable with no horizontal scroll | Assumption (mobile) |

## Server-side validation without the browser

```bash
# Get a CSRF cookie and token, then post an invalid quantity
curl -s -c /tmp/c.txt http://127.0.0.1:8000/ > /dev/null
TOKEN=$(grep csrftoken /tmp/c.txt | awk '{print $7}')
curl -s -b /tmp/c.txt -H "Referer: http://127.0.0.1:8000/" \
  -d "csrfmiddlewaretoken=$TOKEN&nome=Teste&quantidade=-1" \
  -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
```

Expected: `200` (the form is re-rendered with an error), not `302`, and no product named "Teste" in the list.
