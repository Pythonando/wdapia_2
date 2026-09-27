---
name: load-testing-geral
description: Teste de carga com Locust para QUALQUER projeto Django — sobe a stack em Docker, roda o cenário headless, coleta RPS, p50/p95/p99 e taxa de erro, e compara com o baseline para aprovar ou reprovar. Versão portátil: o locustfile vem vazio e é escrito pelo agente load-test-runner-geral a partir do código do projeto. Use ao terminar/atualizar uma feature, antes de deploy, ao investigar lentidão sob concorrência, ou quando o usuário pedir "teste de carga", "load test", "locust", "quantos requests por segundo aguenta", "stress test", "benchmark de performance".
keywords:
  - teste de carga
  - load test
  - locust
  - stress test
  - benchmark
  - requests por segundo
  - rps
  - p95
  - p99
  - latência
  - throughput
  - regressão de performance
file_patterns:
  - '**/views.py'
  - '**/api.py'
  - '**/urls.py'
  - '**/models.py'
confidence: 0.9
---

# Teste de carga com Locust (versão geral)

Mede quanta carga a aplicação aguenta **de verdade**, em runtime — throughput
(req/s), latência por percentil (p50/p95/p99), taxa de erro e o ponto em que a
stack degrada. Complementa a análise estática de performance: aquela lê o código,
esta mede o comportamento.

Fluxo: **configurar (1ª vez) → subir a stack → rodar o cenário → relatório →
comparar com o baseline → aprovar ou reprovar**.

## O que é genérico e o que é do projeto

Esta skill não contém nada de um projeto específico. Três arquivos começam
**vazios/em branco** e precisam ser preenchidos uma vez por projeto:

| Arquivo | Estado inicial | Quem preenche |
| --- | --- | --- |
| `scripts/locustfile.py` | vazio (só um comentário) | agente `load-test-runner-geral` |
| `scripts/seed_load_test_users.py` | hooks vazios, `SEED_CONFIGURED = False` | agente |
| `scripts/loadtest.env` | tudo comentado, `LOADTEST_ENV_CONFIGURED=0` | agente |

`python3 scripts/check_setup.py` diz o que falta (exit 0 = pronto). O
`run_load_test.sh` roda essa checagem e aborta com exit code **3** se algo
estiver pendente — não existe run "verde" sobre um locustfile vazio.

> Para configurar: acione o agente **`load-test-runner-geral`**. Manualmente,
> siga `references/discovery-checklist.md` e `references/locustfile-template.md`.

## Quando usar / não usar

Usar: depois de criar/alterar feature no ciclo de request (views, APIs,
middlewares, queries, templates); antes de deploy sensível; ao investigar
lentidão que só aparece sob concorrência; para criar/atualizar o **baseline**.

Não usar: para achar N+1 sem rodar nada (auditoria estática); para medir
complexidade de código; contra **produção real com usuários** sem autorização
explícita.

## Pré-requisitos

| Requisito | Como obter |
| --- | --- |
| Docker + Compose v2 | `docker --version && docker compose version` |
| Locust (só sem Docker) | `uvx locust --version` ou `pip/uv add --dev locust` |
| Um Dockerfile que sobe o app | o do próprio projeto (`LOADTEST_WEB_DOCKERFILE`) |
| Alvo acessível | stack local em Docker (recomendado) ou `runserver` |

> **Nunca** rode carga contra produção sem autorização explícita. O alvo padrão
> é a stack local `http://web:<porta>`.

## Arquivos

```
.claude/skills/load-testing-geral/
├── SKILL.md
├── scripts/
│   ├── locustfile.py                 ← VAZIO: cenários do projeto
│   ├── seed_load_test_users.py       ← genérico + hooks do projeto
│   ├── loadtest.env                  ← env da stack de teste (banco, chaves fake…)
│   ├── check_setup.py                ← o que falta configurar?
│   ├── list_routes.py                ← lista as rotas do projeto Django
│   ├── _django_bootstrap.py          ← django.setup() sem hardcode
│   ├── run_load_test.sh              ← orquestrador ponta a ponta
│   ├── analyze_results.py            ← CSV do Locust → relatório MD + gate
│   ├── Dockerfile.locust             ← imagem do Locust
│   └── docker-compose.loadtest.yml   ← db (+redis) + web (+worker) + locust
├── references/
│   ├── discovery-checklist.md        ← o que levantar do projeto
│   ├── locustfile-template.md        ← esqueleto do locustfile
│   ├── locust-patterns.md            ← como adicionar tasks
│   └── thresholds.md                 ← SLOs e critérios de aprovação
├── baselines/                        ← baselines (JSON), um por cenário
└── reports/                          ← saída de cada execução (gitignored)
```

## Passo a passo

### Passo 0 — Configurar (só na primeira vez, ou quando o projeto mudar)

```bash
python3 .claude/skills/load-testing-geral/scripts/check_setup.py
```

Pendente → siga `references/discovery-checklist.md` e preencha os três arquivos
da tabela acima. Dois cuidados que valem para qualquer projeto:

- O **seed** precisa fazer o usuário de teste passar pelo gate de acesso do app
  (assinatura, e-mail verificado, onboarding…) e **abortar** se não passar
  (`has_access`). Senão o teste mede o redirect do middleware.
- O `loadtest.env` usa valores **placeholder**. O `.env` do projeto NÃO é
  carregado de propósito: ele pode ter a URL do banco de produção e chaves de
  serviços pagos.

### Passo 1 — Definir o escopo

1. **O que mudou?** Endpoints tocados (`git diff --name-only <branch-principal>...HEAD`).
2. **Qual cenário?** `smoke`, `baseline`, `stress`, `spike` ou `soak`.
3. **O locustfile cobre esses endpoints?** Senão, adicione `@task`
   (`references/locust-patterns.md`).

### Passo 2 — Rodar

O jeito curto (build, seed, run, relatório e gate):

```bash
cd .claude/skills/load-testing-geral/scripts
./run_load_test.sh --scenario baseline
```

```bash
./run_load_test.sh --scenario smoke                  # 10 users / 1 min
./run_load_test.sh --scenario baseline               # 50 users / 5 min — padrão
./run_load_test.sh --scenario stress                 # 300 users / 10 min — busca o teto
./run_load_test.sh --scenario spike                  # pico de 200 users
./run_load_test.sh --users 120 --spawn-rate 10 --run-time 3m
./run_load_test.sh --host http://localhost:8000 --no-docker   # alvo já no ar
./run_load_test.sh --tags minha_feature              # só a feature
./run_load_test.sh --with-worker                     # sobe Redis + worker
./run_load_test.sh --allow-expensive                 # libera tasks caras (custo real!)
./run_load_test.sh --update-baseline                 # promove o resultado a baseline
```

Por baixo: sobe `db` (+`redis`), espera `healthy`, sobe `web` (+`worker`),
semeia usuários dentro do container, roda o Locust headless, gera o relatório e
derruba a stack (`--keep-up` mantém).

> `--exit-code-on-error 0` desliga o exit code padrão do Locust; quem decide
> aprovado/reprovado é o gate do `analyze_results.py`.

### Passo 3 — Interpretar

Leia `references/thresholds.md`. Resumo do gate:

| Critério | Aprovado | Atenção | Reprovado |
| --- | --- | --- | --- |
| Taxa de erro | < 0,5% | 0,5–1% | > 1% |
| p95 agregado | ≤ 800 ms | 800–1500 ms | > 1500 ms |
| p99 agregado | ≤ 1500 ms | 1500–3000 ms | > 3000 ms |
| Regressão de p95 vs baseline | ≤ +10% | +10–25% | > +25% |
| Queda de RPS vs baseline | ≤ 10% | 10–20% | > 20% |

Qualquer endpoint individual com p99 > 3 s ou erro > 1% também reprova, mesmo
que o agregado passe.

### Passo 4 — Baseline (só quando fizer sentido)

Promova quando o resultado for **aprovado** e representar o novo estado
esperado. Nunca promova um run reprovado para "fazer o gate passar". Para o
primeiro baseline, rode 3× com a máquina ociosa (ver `thresholds.md`).

## Cenários

| Cenário | Users | Spawn | Duração | Para quê |
| --- | --- | --- | --- | --- |
| `smoke` | 10 | 2/s | 1 min | O cenário roda? Endpoint novo responde? |
| `baseline` | 50 | 5/s | 5 min | Medida oficial, comparável entre runs |
| `stress` | 300 | 10/s | 10 min | Onde quebra, qual o teto de RPS |
| `spike` | 200 | 50/s | 3 min | Comportamento em pico súbito |
| `soak` | 30 | 3/s | 30 min | Vazamento de memória/conexão |

## Checklist antes de reportar

- [ ] `check_setup.py` retornou PRONTO.
- [ ] A stack subiu com `DEBUG=False` (com `True` o Django guarda todas as
      queries em memória e distorce a medição).
- [ ] Os usuários de teste passam pelo gate de acesso (senão mede-se o redirect).
- [ ] Rodou ≥ 1 min **após** o ramp-up.
- [ ] Os endpoints da feature aparecem no CSV com contagem > 0.
- [ ] O baseline comparado é do mesmo cenário, config de servidor e host.
- [ ] A taxa de erro foi investigada (4xx esperado ≠ 5xx real; erro do teste ≠
      erro do app).

## Armadilhas (valem para qualquer projeto Django)

- **Gate de acesso**: usuário sem a condição do middleware é redirecionado e o
  teste mede o middleware. O seed resolve e se autoverifica.
- **CSRF**: todo POST precisa do `csrfmiddlewaretoken` + `X-CSRFToken`.
- **HTMX**: sem `HX-Request: true` a resposta é outra.
- **Tags não excluem nada.** Sem `--tags`, todas as tasks rodam. Tasks caras
  precisam de guard `if not ALLOW_EXPENSIVE: return` no corpo.
- **View só-POST chamada com GET** devolve 500 e domina a taxa de erro.
- **Lista de ids vazia** faz a task retornar sem emitir request: run "verde" sem
  medir nada. Semeie dados.
- **`${VAR:-default}` com `{}` no compose** quebra no primeiro `}` — deixe vazio
  e aplique o default no locustfile.
- **`--tags` sem `--user-classes`** pode deixar uma classe sem tasks e o Locust
  entra em loop com 0 requests.
- **Config do servidor** (workers × threads) e alvo diferentes invalidam a
  comparação com o baseline; registre no relatório (`LOADTEST_SERVER_CONFIG`).
- **`.env` do projeto não é carregado** — evita escrever no banco de produção e
  gastar com serviços pagos.
- **Docker Compose antigo** (< 2.20): a skill evita `depends_on.required` e
  `env_file.required`; Redis/worker vêm por `--profile`.

## Referências

- `references/discovery-checklist.md` — o que levantar do projeto.
- `references/locustfile-template.md` — esqueleto para escrever o locustfile.
- `references/locust-patterns.md` — como adicionar tasks para uma feature nova.
- `references/thresholds.md` — SLOs, critérios de aprovação, calibração.
