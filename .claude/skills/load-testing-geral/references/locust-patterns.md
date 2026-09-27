# Como adicionar uma feature nova ao cenário de carga

Quando uma feature cria ou altera endpoints, ela precisa entrar no
`scripts/locustfile.py` — senão o teste passa medindo código antigo e o gate dá
uma falsa sensação de segurança. (Esqueleto completo: `locustfile-template.md`.)

## 1. Identifique os endpoints da feature

```bash
BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||' || echo main)
git diff --name-only "$BASE"...HEAD -- '*/urls.py'
git diff "$BASE"...HEAD -- '*/urls.py' | grep '^+.*path('
python3 .claude/skills/load-testing-geral/scripts/list_routes.py --filter <trecho>
```

## 2. Escolha a classe certa

- Rota pública (sem login) → a classe anônima.
- Rota autenticada → a classe autenticada (já faz login e tem cookies/CSRF).

## 3. Escreva a task

```python
@tag('minha_feature', 'read')
@task(5)
def minha_pagina(self):
    self.client.get('/minha/rota/', name='GET /minha/rota/')
```

O `name=` é obrigatório e **precisa ser estável**. Sem ele, cada URL com id
diferente vira uma linha separada no relatório, sem estatística útil:

```python
# ❌ gera 500 linhas distintas no CSV
self.client.get(f'/itens/{item_id}/')

# ✅ agrega tudo em uma linha
self.client.get(f'/itens/{item_id}/', name='GET /itens/[id]/')
```

### POST (precisa de CSRF)

```python
@tag('minha_feature', 'write')
@task(1)
def criar(self):
    self.refresh_csrf()
    self.client.post(
        '/itens/criar/', name='POST /itens/criar/',
        data={'csrfmiddlewaretoken': self.csrftoken or '', 'nome': 'teste'},
        headers=self.csrf_headers({'Referer': f'{self.host}/itens/'}),
    )
```

### Rota HTMX

Sem `HX-Request: true` a view devolve a página inteira, e o custo medido não é o
real. Acrescente o header em `csrf_headers` (ver template).

### Quando um status "de erro" é esperado

Use `catch_response` para não poluir a taxa de erro com comportamento correto
(ex.: 404 para item de outro usuário) — ver `locustfile-template.md`.

## 4. Calibre o peso (`@task(n)`)

O peso deve refletir o **tráfego real**, não a importância da feature. Pesos
irreais medem uma aplicação que não existe. Regra de bolso: página inicial e
listagens altos, detalhes médios, polling alto (repete a cada poucos segundos),
escrita baixa.

## 5. Marque com tags

Sempre inclua (a) uma tag de domínio e (b) `read` ou `write`. Permite
`--tags minha_feature` para focar na feature nova e `--exclude-tags write` para
um run não destrutivo.

## 6. Isole o que custa dinheiro ou é destrutivo

⚠️ **Tag não é proteção.** No Locust, `@tag` é só um filtro *opcional*: sem
`--tags`, **todas** as tasks rodam. Marcar uma task como `expensive` e parar aí
faz um run comum chamar o serviço pago.

Chamadas a LLM, envio de e-mail, criação de cobrança e upload exigem **duas**
camadas — a tag (para filtrar) **e** um guard explícito no corpo:

```python
@tag('minha_feature_write', 'write', 'expensive')
@task(1)
def operacao_cara(self):
    if not ALLOW_EXPENSIVE:      # env LOADTEST_ALLOW_EXPENSIVE=1
        return
    ...
```

## 7. Valide

```bash
./run_load_test.sh --scenario smoke --tags minha_feature
```

Confirme que a rota nova aparece com contagem > 0. Com 0, a task nunca foi
selecionada — quase sempre erro de tag ou `return` antecipado por lista de ids
vazia (falta de dados no seed).

## Erros comuns

| Sintoma | Causa provável |
| --- | --- |
| 100% de erro em tudo | Usuários não semeados, ou senha divergente |
| Tudo com 302 | Usuário não passa no gate de acesso → o seed não o satisfaz |
| 403 nos POSTs | CSRF ausente, ou `Referer` faltando em HTTPS |
| Centenas de linhas no CSV | Faltou `name=` em URL com id |
| 500 em 100% de uma rota GET | A view só trata POST |
| p99 altíssimo só no primeiro minuto | Ramp-up; ignore ou aumente `--run-time` |
| Endpoint com 0 requests | Tag errada, ou `return` por lista de ids vazia |
| RPS baixo e CPU do host em 100% | O Locust está competindo com o app pela CPU |
| Run com 0 requests e log "No tasks defined" | `--tags` deixou uma classe sem tasks; use `--user-classes` |
