# Thresholds e critérios de aprovação

Estes são os limites aplicados por `scripts/analyze_results.py`. Eles definem o
que significa "o novo código atende aos padrões atuais".

## Por que percentis, e não média

A média esconde a cauda. Um endpoint com média de 200 ms pode ter p99 de 8 s —
1% dos usuários com uma experiência inaceitável. Regra prática:

| Percentil | O que significa |
| --- | --- |
| **p50** | A experiência típica. Se está ruim, está ruim para todo mundo. |
| **p95** | O usuário insatisfeito. É o número de SLO mais usado. |
| **p99** | A cauda. Revela lock de banco, GC, pool esgotado, cold start. |
| **máx** | Um único evento. Útil para achar timeout, não para SLO. |

Um p99 muito maior que o p95 quase sempre aponta contenção (pool de conexões,
lock, worker saturado), não código lento.

## Limites absolutos

Aplicados sobre o **agregado** de todas as requests.

| Métrica | ✅ Aprovado | ⚠️ Atenção | ❌ Reprovado |
| --- | --- | --- | --- |
| Taxa de erro | < 0,5% | 0,5% – 1% | > 1% |
| p95 | ≤ 800 ms | 800 – 1500 ms | > 1500 ms |
| p99 | ≤ 1500 ms | 1500 – 3000 ms | > 3000 ms |
| Requests coletadas | ≥ 100 | — | < 100 |

Menos de 100 requests reprova por princípio: o resultado não é estatisticamente
utilizável, e um p99 sobre 20 amostras é ruído.

## Limites por endpoint

O agregado dilui. Um endpoint lento chamado 1× a cada 100 requests some na média
geral e ainda assim trava o usuário que o acessa. Por isso, **qualquer** endpoint
individual reprova o run se:

- p99 > 3000 ms, **ou**
- taxa de erro > 1%.

## Regressão vs baseline

Comparado ao `baselines/<cenário>.json`.

| Métrica | ✅ Aprovado | ⚠️ Atenção | ❌ Reprovado |
| --- | --- | --- | --- |
| Aumento de p95 | ≤ +10% | +10% – +25% | > +25% |
| Queda de RPS | ≤ 10% | 10% – 20% | > 20% |

A margem de 10% absorve o ruído normal entre execuções na mesma máquina. Se as
execuções variam mais que isso sem mudança de código, a máquina está com carga
concorrente — rode de novo com a máquina ociosa antes de acreditar no número.

## Como ajustar

Os valores ficam no dicionário `THRESHOLDS` em `scripts/analyze_results.py`. Só
afrouxe um limite com justificativa registrada — o valor de um gate está em ele
ser estável ao longo do tempo. Afrouxar para fazer o build passar transforma o
gate em decoração.

Para um teste pontual, dá para sobrescrever os limites do **locustfile** (que
controla o exit code do Locust, não o do gate) por env var:

```bash
LOADTEST_P95_MS=1200 LOADTEST_P99_MS=2500 ./run_load_test.sh --scenario baseline
```

## Comparabilidade

Um baseline só é comparável a um run com:

- mesmo **cenário** (users / spawn rate / duração),
- mesma **configuração de servidor** (`GUNICORN_WORKERS` × `GUNICORN_THREADS`),
- mesmo **alvo** (local em Docker ≠ ambiente de deploy real),
- máquina em estado parecido (sem build/IDE pesado concorrendo).

Mudou qualquer um desses? O delta vs baseline é informativo, não conclusivo — e
o relatório deve dizer isso explicitamente. O `analyze_results.py` já ignora a
comparação quando o cenário do baseline difere do run.

## Calibrando o primeiro baseline

1. Rode `--scenario smoke` e confirme que o cenário funciona (0 erros de login,
   endpoints com contagem > 0).
2. Rode `--scenario baseline` **três vezes** com a máquina ociosa.
3. Confira que o p95 varia menos de 10% entre as três.
4. Promova a mediana das três: `./run_load_test.sh --scenario baseline --update-baseline`.

Se as três execuções variarem muito, o ambiente não está estável o suficiente
para servir de gate — resolva isso antes, senão o gate vai gerar alarme falso e
perder credibilidade.
