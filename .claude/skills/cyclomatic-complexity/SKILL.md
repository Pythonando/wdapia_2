---
name: cyclomatic-complexity
description: Mede e interpreta complexidade ciclomática e manutenibilidade com radon. Use ao auditar qualidade de código Python/Django, decidir o que refatorar, revisar um diff antes de commit/PR, ou quando o usuário pedir "complexidade", "radon", "código complexo demais", "refatorar função grande".
keywords:
  - complexidade ciclomática
  - cyclomatic complexity
  - radon
  - maintainability index
  - refatoração
  - code quality
  - halstead
  - dívida técnica
file_patterns:
  - '**/*.py'
confidence: 0.85
---

# Complexidade ciclomática com radon

Mede quantos caminhos independentes existem em cada função/método. Alta
complexidade significa mais casos de teste necessários, mais chance de bug e
código mais difícil de mudar. Esta skill roda o [radon](https://radon.readthedocs.io),
converte a saída em relatório priorizado e oferece um *gate* de CI.

## Quando usar

- Auditoria de qualidade ou levantamento de dívida técnica.
- Antes de refatorar: descobrir **o que** refatorar primeiro.
- Revisão de diff/PR: garantir que a mudança não piorou a complexidade.
- Depois de implementar uma feature grande (views, tasks Celery, serviços de IA).

## Instalação

Radon já está instalado no `venv/` deste repositório (6.0.1), mas **não** consta em
`requirements.txt` — em um ambiente novo (CI, container), instale antes:

```bash
venv/bin/pip install radon        # venv local deste repositório
uvx radon cc apps                 # execução efêmera, não instala nada
uv add --dev radon                # se o projeto passar a ser gerenciado por uv
```

O script localiza o radon sozinho, nesta ordem: `$RADON` → `venv/bin/radon` →
`venv/bin/python -m radon` → `radon` no PATH → `uvx radon`. Se nada existir, ele
falha com as instruções de instalação acima.

## Uso

Sempre a partir da raiz do projeto:

```bash
# Relatório completo (apps/, core/, middlewares/, manage.py)
.claude/skills/cyclomatic-complexity/scripts/check_complexity.sh

# Um app específico
.claude/skills/cyclomatic-complexity/scripts/check_complexity.sh apps/artificial_intelligence

# Só o que mudou em relação à branch base — ideal para revisão de PR
.claude/skills/cyclomatic-complexity/scripts/check_complexity.sh --changed origin/master

# Listar tudo, inclusive rank B, e salvar em Markdown
.claude/skills/cyclomatic-complexity/scripts/check_complexity.sh \
    --min-rank B --top 0 --markdown docs/complexity-report.md
```

Se o `.sh` não tiver permissão de execução, chame direto:
`python .claude/skills/cyclomatic-complexity/scripts/complexity_report.py`.

### Flags principais

| Flag | Efeito |
| --- | --- |
| `--min-rank {A..F}` | Rank mínimo listado na tabela (padrão `C`). |
| `--fail-on {A..F}` | Rank que faz o comando sair com código 1 (padrão `D`, ou seja CC >= 21). |
| `--changed REF` | Analisa só arquivos `.py` alterados vs. `REF` (via `git diff`). |
| `--baseline FILE` | Só falha em blocos **novos** ou que **pioraram** desde o baseline. |
| `--update-baseline` | Grava o estado atual como baseline e sai com 0. |
| `--mi-threshold N` | Lista arquivos com índice de manutenibilidade abaixo de `N` (padrão 20). |
| `--top N` | Máximo de linhas na tabela; `0` mostra todas (padrão 25). |
| `--markdown F` / `--json F` | Grava o relatório / os dados brutos. |
| `--ignore a,b` | Diretórios ignorados (padrão já exclui `venv`, `migrations`, `media`, `graphify-out`, `staticfiles`). |

Códigos de saída: `0` limpo · `1` limite estourado · `2` erro de execução.

## Escala de ranks

| Rank | CC | Leitura | Ação |
| --- | --- | --- | --- |
| A | 1–5 | Simples | Nenhuma. |
| B | 6–10 | Bem estruturado | Nenhuma. |
| C | 11–20 | Levemente complexo | Observar; refatorar se for tocar no código. |
| D | 21–30 | Alto risco | Refatorar — muitos caminhos para testar. |
| E | 31–40 | Alarmante | Refatorar com prioridade. |
| F | 41+ | Erro de design | Quebrar em unidades menores já. |

O **índice de manutenibilidade (MI)** é uma métrica separada, por arquivo, de 0 a
100 (combina volume de Halstead, CC e linhas). MI < 20 = arquivo difícil de manter,
geralmente por tamanho + complexidade acumulados.

## Como interpretar e agir

1. **Priorize por risco, não pelo número.** Um CC 25 em `payments/webhooks.py`
   (dinheiro, idempotência) vale mais atenção que CC 25 num script utilitário.
2. **Cruze com cobertura de teste.** CC alto informa quantos casos de teste o
   bloco exige; se o CC é 22 e existem 3 testes, o buraco está aí.
3. **Não persiga o número.** Extrair 6 helpers de uso único só para baixar o rank
   dispersa a lógica e piora a leitura. A meta é código mais claro; o rank é o sintoma.
4. **Ignore falsos positivos conhecidos**: migrations do Django, dispatchers com
   longos `if/elif` sobre tipos de evento, e `Meta`/config declarativos.

Padrões de refatoração para cada causa (ninhos de `if`, dispatch, validações
encadeadas, `try/except` extensos, views Django gordas) estão em
[references/refactoring-patterns.md](references/refactoring-patterns.md).

## Usando baseline num código legado

Rodar o gate com `--fail-on D` num repositório existente costuma acusar dezenas de
blocos antigos. O baseline congela esse passivo e faz o gate cobrar só o que for
novo:

```bash
# 1. congela o estado atual
.claude/skills/cyclomatic-complexity/scripts/check_complexity.sh \
    --baseline .complexity-baseline.json --update-baseline

# 2. daí em diante, só falha em bloco novo ou que piorou
.claude/skills/cyclomatic-complexity/scripts/check_complexity.sh \
    --baseline .complexity-baseline.json
```

Commite o `.complexity-baseline.json`. Ao refatorar e reduzir a complexidade,
rode `--update-baseline` de novo para travar a melhoria.

## Comandos radon crus

Quando precisar de algo que o wrapper não cobre:

```bash
radon cc apps -s -a -nc          # complexidade, ordenada, só rank C+, com média
radon mi apps -s                 # índice de manutenibilidade por arquivo
radon raw apps -s                # LOC, LLOC, comentários
radon hal apps                   # métricas de Halstead (esforço, bugs estimados)
radon cc apps -j                 # JSON (formato consumido pelo script)
```

## Depois de refatorar

Este repositório exige rodar o agente `doc-sync-onboarding` como última etapa de
qualquer alteração de código (ver `CLAUDE.md`). Rodar o relatório sozinho não
altera código e não dispara essa regra; refatorações resultantes, sim.
