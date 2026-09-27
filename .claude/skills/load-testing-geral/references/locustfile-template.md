# Esqueleto do locustfile

O `scripts/locustfile.py` desta skill vem **vazio**. Este é o esqueleto para
preenchê-lo. Adapte cada bloco marcado com `# ADAPTAR` ao que você levantou em
`discovery-checklist.md`, e apague os blocos que o projeto não usa (HTMX, SSE,
tasks caras).

```python
"""Cenários de teste de carga de <PROJETO>.

    locust -f locustfile.py --host http://web:8000 \
        --headless --users 50 --spawn-rate 5 --run-time 5m \
        --csv results/run --html results/run.html --exit-code-on-error 0

Variáveis de ambiente:
    LOADTEST_USER_PATTERN    valor do campo de login, com {i} (default abaixo)
    LOADTEST_PASSWORD        senha dos usuários semeados
    LOADTEST_USER_POOL       quantos usuários existem no banco (default 50)
    LOADTEST_FAIL_RATIO / LOADTEST_P95_MS / LOADTEST_P99_MS   limites do gate
    LOADTEST_ALLOW_EXPENSIVE libera tasks caras (default: desligado)

Tags: <liste as tags que existirem>.

Atenção: no Locust, `@tag` NÃO exclui a task de um run sem `--tags` — todas
rodam. Tasks caras precisam de guard no corpo (ALLOW_EXPENSIVE).
"""

from __future__ import annotations

import itertools
import logging
import os
import random
import re

from locust import HttpUser, between, events, tag, task

logger = logging.getLogger(__name__)

# `or` (e não o default do getenv): o compose exporta a variável vazia quando o
# host não a define, e '' é um padrão inválido.
USER_PATTERN = os.getenv('LOADTEST_USER_PATTERN') or 'loadtest+{i}@example.com'
PASSWORD = os.getenv('LOADTEST_PASSWORD', 'LoadTest!2024')
USER_POOL = int(os.getenv('LOADTEST_USER_POOL', '50'))
ALLOW_EXPENSIVE = os.getenv('LOADTEST_ALLOW_EXPENSIVE', '').lower() in ('1', 'true', 'yes')

MAX_FAIL_RATIO = float(os.getenv('LOADTEST_FAIL_RATIO', '0.01'))
MAX_P95_MS = float(os.getenv('LOADTEST_P95_MS', '800'))
MAX_P99_MS = float(os.getenv('LOADTEST_P99_MS', '1500'))

CSRF_INPUT_RE = re.compile(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']')
_user_cycle = itertools.cycle(range(1, USER_POOL + 1))  # 1 usuário do pool por VU


class DjangoUserMixin:
    """Login por sessão + CSRF do Django.  # ADAPTAR (fatos 3, 4, 5, 10)"""

    csrftoken: str | None = None
    identity: str = ''

    def csrf_headers(self, extra: dict | None = None) -> dict:
        headers = {'X-CSRFToken': self.csrftoken} if self.csrftoken else {}
        # Só se o projeto usa HTMX: headers['HX-Request'] = 'true'
        headers.update(extra or {})
        return headers

    def refresh_csrf(self) -> None:
        self.csrftoken = self.client.cookies.get('csrftoken')

    def login(self) -> bool:
        self.identity = USER_PATTERN.format(i=next(_user_cycle))
        with self.client.get('/login/', name='GET /login/', catch_response=True) as r:  # ADAPTAR URL
            if r.status_code != 200:
                r.failure(f'login page {r.status_code}')
                return False
            match = CSRF_INPUT_RE.search(r.text)
            token = match.group(1) if match else self.client.cookies.get('csrftoken')
            r.success()
        if not token:
            logger.warning('CSRF token não encontrado na página de login')
            return False
        self.csrftoken = token

        with self.client.post(
            '/login/',  # ADAPTAR URL
            name='POST /login/',
            data={'csrfmiddlewaretoken': token, 'username': self.identity, 'password': PASSWORD},  # ADAPTAR campos
            headers=self.csrf_headers({'Referer': f'{self.host}/login/'}),
            allow_redirects=False,
            catch_response=True,
        ) as r:
            # ADAPTAR o sinal de sucesso: login clássico = 302; HTMX = 200 + header
            # HX-Redirect. Credencial errada costuma re-renderizar o form com 200,
            # e isso NÃO pode contar como sucesso.
            if r.status_code != 302:
                r.failure(f'login recusado para {self.identity} ({r.status_code}) — usuário semeado?')
                return False
            r.success()
        self.refresh_csrf()
        return True


class AnonymousUser(HttpUser):
    """Visitante sem login: páginas públicas.  # ADAPTAR (fato 8)"""

    weight = 1
    wait_time = between(1, 3)

    @tag('anon', 'read')
    @task(10)
    def landing(self):
        self.client.get('/', name='GET /')


class AuthenticatedUser(DjangoUserMixin, HttpUser):
    """Usuário logado navegando pelo app."""

    weight = 9
    wait_time = between(1, 4)

    def on_start(self):
        self.item_ids: list[int] = []
        if not self.login():
            # Sem sessão válida todas as rotas viram redirect ao login e a
            # medição perde sentido — melhor parar este usuário virtual.
            logger.error('Login falhou para %s — o seed rodou?', self.identity)
            self.stop()
            return
        self.discover_ids()

    def discover_ids(self):
        """Coleta ids reais para exercitar rotas de detalhe.  # ADAPTAR"""
        with self.client.get('/itens/', name='GET /itens/', catch_response=True) as r:
            if r.status_code == 200:
                self.item_ids = [int(pk) for pk in re.findall(r'/itens/(\d+)/', r.text)][:10]
                r.success()
        if not self.item_ids:
            logger.warning('Nenhum item para %s — semeie dados (hook seed_data), senão '
                           'as rotas de detalhe não são exercitadas.', self.identity)

    @tag('itens', 'read')
    @task(8)
    def lista(self):
        self.client.get('/itens/', name='GET /itens/')

    @tag('itens', 'read')
    @task(5)
    def detalhe(self):
        if not self.item_ids:
            return
        pk = random.choice(self.item_ids)
        self.client.get(f'/itens/{pk}/', name='GET /itens/[id]/')  # name estável!

    @tag('itens_write', 'write', 'expensive')
    @task(1)
    def operacao_cara(self):
        """Só se a rota tem efeito colateral/custo (LLM, e-mail, cobrança)."""
        if not ALLOW_EXPENSIVE:  # a tag sozinha NÃO impede a execução
            return
        self.refresh_csrf()
        self.client.post(
            '/itens/criar/',
            name='POST /itens/criar/',
            data={'csrfmiddlewaretoken': self.csrftoken or '', 'nome': 'teste de carga'},
            headers=self.csrf_headers({'Referer': f'{self.host}/itens/'}),
        )


@events.quitting.add_listener
def _apply_thresholds(environment, **_kwargs):
    """Exit code do processo conforme os limites (o gate oficial é o analyze_results.py)."""
    stats = environment.stats.total
    failures = []
    if stats.num_requests == 0:
        failures.append('nenhuma request executada')
    else:
        if stats.fail_ratio > MAX_FAIL_RATIO:
            failures.append(f'taxa de erro {stats.fail_ratio:.2%} > {MAX_FAIL_RATIO:.2%}')
        p95 = stats.get_response_time_percentile(0.95)
        p99 = stats.get_response_time_percentile(0.99)
        if p95 and p95 > MAX_P95_MS:
            failures.append(f'p95 {p95:.0f}ms > {MAX_P95_MS:.0f}ms')
        if p99 and p99 > MAX_P99_MS:
            failures.append(f'p99 {p99:.0f}ms > {MAX_P99_MS:.0f}ms')
    for reason in failures:
        logger.error('THRESHOLD VIOLADO: %s', reason)
    environment.process_exit_code = 1 if failures else 0
```

## Padrões adicionais

### Login/autenticação diferente

- **Token/JWT (DRF)**: em `login()`, faça POST no endpoint de token, guarde o
  `access` e envie `Authorization: Bearer ...` via `self.client.headers.update`.
  Descarte a lógica de CSRF.
- **HTMX**: envie `HX-Request: true` (sem ele a view devolve a página inteira em
  vez do fragmento e o custo medido não é o real). Login HTMX responde
  `200` + header `HX-Redirect` em vez de `302`.

### Streaming / SSE

Sob gunicorn `gthread`, cada stream aberto ocupa **uma thread** enquanto durar,
então ele define o teto de concorrência da feature. Meça-o limitando o tempo de
hold para o run não travar:

```python
SSE_HOLD_S = float(os.getenv('LOADTEST_SSE_HOLD_S', '15'))

@tag('sse', 'read')
@task(3)
def stream(self):
    started = time.monotonic()
    with self.client.get('/eventos/', name='GET /eventos/ (sse)',
                         headers={'Accept': 'text/event-stream'}, stream=True,
                         timeout=SSE_HOLD_S + 30, catch_response=True) as r:
        if r.status_code != 200:
            r.failure(f'sse {r.status_code}')
            return
        try:
            for line in r.iter_lines(decode_unicode=True):
                if time.monotonic() - started >= SSE_HOLD_S:
                    break
        finally:
            r.close()
        r.success()
```

### Status "de erro" esperado

```python
with self.client.get(f'/itens/{pk}/', name='GET /itens/[id]/', catch_response=True) as r:
    if r.status_code in (200, 404):
        r.success()      # 404 é esperado se o item não é do usuário
    else:
        r.failure(f'status inesperado {r.status_code}')
```
