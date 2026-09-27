#!/usr/bin/env python3
"""Converte o CSV do Locust em relatório de performance + gate de aprovação.

    python3 analyze_results.py \
        --csv-prefix ../reports/2026-08-10T12-00-00/baseline \
        --baseline ../baselines/baseline.json \
        --scenario baseline \
        --output ../reports/2026-08-10T12-00-00/RELATORIO.md

Exit code: 0 = APROVADO (ou APROVADO COM RESSALVAS), 1 = REPROVADO.

Sem dependências além da stdlib — roda em qualquer Python 3.11+.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Thresholds (ver references/thresholds.md)
# --------------------------------------------------------------------------- #

THRESHOLDS = {
    'fail_ratio_ok': 0.005,        # 0,5%
    'fail_ratio_fail': 0.01,       # 1%
    'p95_ok_ms': 800,
    'p95_fail_ms': 1500,
    'p99_ok_ms': 1500,
    'p99_fail_ms': 3000,
    'endpoint_p99_fail_ms': 3000,
    'endpoint_fail_ratio_fail': 0.01,
    'p95_regression_ok': 0.10,     # +10%
    'p95_regression_fail': 0.25,   # +25%
    'rps_drop_ok': 0.10,           # -10%
    'rps_drop_fail': 0.20,         # -20%
    'min_requests': 100,
}

PASS, WARN, FAIL = 'APROVADO', 'APROVADO COM RESSALVAS', 'REPROVADO'


# --------------------------------------------------------------------------- #
# Leitura do CSV do Locust
# --------------------------------------------------------------------------- #


def _num(row: dict, *keys: str, default: float = 0.0) -> float:
    """Lê a primeira chave presente e converte para float.

    O Locust mudou nomes de colunas entre versões; aceitamos os aliases.
    """
    for key in keys:
        value = row.get(key)
        if value not in (None, '', 'N/A'):
            try:
                return float(value)
            except ValueError:
                continue
    return default


def read_stats(csv_prefix: Path) -> dict:
    stats_path = Path(f'{csv_prefix}_stats.csv')
    if not stats_path.exists():
        raise SystemExit(
            f'ERRO: {stats_path} não encontrado. O Locust rodou com --csv?'
        )

    endpoints: list[dict] = []
    aggregated: dict | None = None

    with stats_path.open(encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            name = row.get('Name', '')
            method = row.get('Type', '') or ''
            requests = _num(row, 'Request Count')
            failures = _num(row, 'Failure Count')

            entry = {
                'name': name if method in ('', 'Aggregated') else f'{method} {name}',
                'requests': int(requests),
                'failures': int(failures),
                'fail_ratio': (failures / requests) if requests else 0.0,
                'rps': _num(row, 'Requests/s'),
                'avg_ms': _num(row, 'Average Response Time'),
                'min_ms': _num(row, 'Min Response Time'),
                'max_ms': _num(row, 'Max Response Time'),
                'p50_ms': _num(row, '50%', 'Median Response Time'),
                'p75_ms': _num(row, '75%'),
                'p90_ms': _num(row, '90%'),
                'p95_ms': _num(row, '95%'),
                'p99_ms': _num(row, '99%'),
            }

            if name == 'Aggregated' or method == 'Aggregated':
                entry['name'] = 'Aggregated'
                aggregated = entry
            else:
                endpoints.append(entry)

    if aggregated is None:
        raise SystemExit('ERRO: linha "Aggregated" ausente no CSV do Locust.')

    return {'aggregated': aggregated, 'endpoints': endpoints}


def read_failures(csv_prefix: Path) -> list[dict]:
    path = Path(f'{csv_prefix}_failures.csv')
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as handle:
        return [
            {
                'name': f"{row.get('Method', '')} {row.get('Name', '')}".strip(),
                'error': row.get('Error', ''),
                'occurrences': int(_num(row, 'Occurrences', 'Occurrence')),
            }
            for row in csv.DictReader(handle)
        ]


def read_peak_rps(csv_prefix: Path) -> tuple[float, int]:
    """Maior RPS e maior número de usuários vistos no histórico."""
    path = Path(f'{csv_prefix}_stats_history.csv')
    if not path.exists():
        return 0.0, 0
    peak_rps = 0.0
    peak_users = 0
    with path.open(encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row.get('Name') not in ('Aggregated', ''):
                continue
            peak_rps = max(peak_rps, _num(row, 'Requests/s'))
            peak_users = max(peak_users, int(_num(row, 'User Count')))
    return peak_rps, peak_users


# --------------------------------------------------------------------------- #
# Gate
# --------------------------------------------------------------------------- #


def evaluate(stats: dict, baseline: dict | None) -> dict:
    agg = stats['aggregated']
    checks: list[dict] = []

    def add(label, status, detail):
        checks.append({'label': label, 'status': status, 'detail': detail})

    # --- volume mínimo ---------------------------------------------------- #
    if agg['requests'] < THRESHOLDS['min_requests']:
        add(
            'Volume de requests',
            FAIL,
            f"{agg['requests']} requests — abaixo do mínimo de "
            f"{THRESHOLDS['min_requests']}. Resultado não é estatisticamente útil.",
        )
    else:
        add('Volume de requests', PASS, f"{agg['requests']} requests coletadas.")

    # --- taxa de erro ------------------------------------------------------ #
    ratio = agg['fail_ratio']
    if ratio > THRESHOLDS['fail_ratio_fail']:
        status = FAIL
    elif ratio > THRESHOLDS['fail_ratio_ok']:
        status = WARN
    else:
        status = PASS
    add(
        'Taxa de erro',
        status,
        f"{ratio:.2%} ({agg['failures']}/{agg['requests']}) — "
        f"limite {THRESHOLDS['fail_ratio_fail']:.1%}",
    )

    # --- latência absoluta ------------------------------------------------- #
    for label, key, ok_key, fail_key in (
        ('p95 agregado', 'p95_ms', 'p95_ok_ms', 'p95_fail_ms'),
        ('p99 agregado', 'p99_ms', 'p99_ok_ms', 'p99_fail_ms'),
    ):
        value = agg[key]
        if value > THRESHOLDS[fail_key]:
            status = FAIL
        elif value > THRESHOLDS[ok_key]:
            status = WARN
        else:
            status = PASS
        add(
            label,
            status,
            f'{value:.0f} ms — alvo ≤ {THRESHOLDS[ok_key]} ms, '
            f'limite {THRESHOLDS[fail_key]} ms',
        )

    # --- endpoints individuais --------------------------------------------- #
    slow = [
        e
        for e in stats['endpoints']
        if e['requests'] > 0 and e['p99_ms'] > THRESHOLDS['endpoint_p99_fail_ms']
    ]
    broken = [
        e
        for e in stats['endpoints']
        if e['requests'] > 0
        and e['fail_ratio'] > THRESHOLDS['endpoint_fail_ratio_fail']
    ]
    if slow or broken:
        detail = []
        if slow:
            detail.append(
                'p99 acima do limite: '
                + ', '.join(f"{e['name']} ({e['p99_ms']:.0f} ms)" for e in slow)
            )
        if broken:
            detail.append(
                'erro acima do limite: '
                + ', '.join(f"{e['name']} ({e['fail_ratio']:.1%})" for e in broken)
            )
        add('Endpoints individuais', FAIL, ' | '.join(detail))
    else:
        add(
            'Endpoints individuais',
            PASS,
            'Nenhum endpoint com p99 > '
            f"{THRESHOLDS['endpoint_p99_fail_ms']} ms ou erro > "
            f"{THRESHOLDS['endpoint_fail_ratio_fail']:.0%}.",
        )

    # --- regressão vs baseline --------------------------------------------- #
    regression = None
    if baseline:
        base_agg = baseline.get('aggregated', {})
        base_p95 = base_agg.get('p95_ms') or 0
        base_rps = base_agg.get('rps') or 0

        if base_p95:
            delta = (agg['p95_ms'] - base_p95) / base_p95
            if delta > THRESHOLDS['p95_regression_fail']:
                status = FAIL
            elif delta > THRESHOLDS['p95_regression_ok']:
                status = WARN
            else:
                status = PASS
            add(
                'Regressão de p95 vs baseline',
                status,
                f"{base_p95:.0f} ms → {agg['p95_ms']:.0f} ms ({delta:+.1%})",
            )
            regression = {'p95_delta': delta}

        if base_rps:
            drop = (base_rps - agg['rps']) / base_rps
            if drop > THRESHOLDS['rps_drop_fail']:
                status = FAIL
            elif drop > THRESHOLDS['rps_drop_ok']:
                status = WARN
            else:
                status = PASS
            add(
                'Throughput vs baseline',
                status,
                f"{base_rps:.1f} req/s → {agg['rps']:.1f} req/s ({-drop:+.1%})",
            )
            regression = {**(regression or {}), 'rps_delta': -drop}
    else:
        add(
            'Comparação com baseline',
            WARN,
            'Nenhum baseline encontrado — este run pode virar o baseline inicial '
            '(--update-baseline).',
        )

    statuses = {c['status'] for c in checks}
    verdict = FAIL if FAIL in statuses else (WARN if WARN in statuses else PASS)

    return {'checks': checks, 'verdict': verdict, 'regression': regression}


# --------------------------------------------------------------------------- #
# Relatório
# --------------------------------------------------------------------------- #

ICON = {PASS: '✅', WARN: '⚠️', FAIL: '❌'}


def render_report(stats, evaluation, meta, failures, peak_rps, peak_users) -> str:
    agg = stats['aggregated']
    lines: list[str] = []
    add = lines.append

    add(f"# 📈 Relatório de Teste de Carga — {meta['project']}")
    add('')
    add(f"**Veredito**: {ICON[evaluation['verdict']]} **{evaluation['verdict']}**")
    add('')
    add('| Campo | Valor |')
    add('| --- | --- |')
    add(f"| Data | {meta['timestamp']} |")
    add(f"| Cenário | `{meta['scenario']}` |")
    add(f"| Alvo | `{meta['host']}` |")
    add(f"| Usuários virtuais | {meta['users']} (spawn {meta['spawn_rate']}/s) |")
    add(f"| Duração | {meta['run_time']} |")
    add(f"| Tags | {meta['tags'] or 'todas'} |")
    add(f"| Commit | `{meta['commit']}` / branch `{meta['branch']}` |")
    add(f"| Config do servidor | {meta['server_config']} |")
    add('')

    add('## 🔢 Métricas agregadas')
    add('')
    add('| Métrica | Valor |')
    add('| --- | --- |')
    add(f"| **Requests/s (média)** | **{agg['rps']:.2f}** |")
    add(f"| Requests/s (pico) | {peak_rps:.2f} (com {peak_users} usuários) |")
    add(f"| Total de requests | {agg['requests']} |")
    add(f"| Falhas | {agg['failures']} ({agg['fail_ratio']:.2%}) |")
    add(f"| **p50 (mediana)** | **{agg['p50_ms']:.0f} ms** |")
    add(f"| p75 | {agg['p75_ms']:.0f} ms |")
    add(f"| p90 | {agg['p90_ms']:.0f} ms |")
    add(f"| **p95** | **{agg['p95_ms']:.0f} ms** |")
    add(f"| **p99** | **{agg['p99_ms']:.0f} ms** |")
    add(f"| Média | {agg['avg_ms']:.0f} ms |")
    add(f"| Mín / Máx | {agg['min_ms']:.0f} ms / {agg['max_ms']:.0f} ms |")
    add('')

    add('## 🚦 Gate de qualidade')
    add('')
    add('| Critério | Status | Detalhe |')
    add('| --- | --- | --- |')
    for check in evaluation['checks']:
        add(
            f"| {check['label']} | {ICON[check['status']]} {check['status']} "
            f"| {check['detail']} |"
        )
    add('')

    add('## 🔍 Latência por endpoint')
    add('')
    add('Ordenado por p99 decrescente — os primeiros são os gargalos.')
    add('')
    add('| Endpoint | Reqs | RPS | p50 | p95 | p99 | Máx | Erros |')
    add('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |')
    ranked = sorted(
        (e for e in stats['endpoints'] if e['requests'] > 0),
        key=lambda e: e['p99_ms'],
        reverse=True,
    )
    for endpoint in ranked:
        flag = ''
        if endpoint['p99_ms'] > THRESHOLDS['endpoint_p99_fail_ms']:
            flag = ' ❌'
        elif endpoint['p99_ms'] > THRESHOLDS['p99_ok_ms']:
            flag = ' ⚠️'
        add(
            f"| `{endpoint['name']}`{flag} | {endpoint['requests']} "
            f"| {endpoint['rps']:.2f} | {endpoint['p50_ms']:.0f} ms "
            f"| {endpoint['p95_ms']:.0f} ms | {endpoint['p99_ms']:.0f} ms "
            f"| {endpoint['max_ms']:.0f} ms | {endpoint['fail_ratio']:.1%} |"
        )
    add('')

    if failures:
        add('## ❌ Erros observados')
        add('')
        add('| Endpoint | Ocorrências | Erro |')
        add('| --- | ---: | --- |')
        for failure in sorted(
            failures, key=lambda f: f['occurrences'], reverse=True
        )[:20]:
            error = failure['error'].replace('|', '\\|')[:160]
            add(f"| `{failure['name']}` | {failure['occurrences']} | {error} |")
        add('')
    else:
        add('## ✅ Erros observados')
        add('')
        add('Nenhum erro registrado durante o teste.')
        add('')

    add('## 📌 Conclusão')
    add('')
    add(_conclusion(evaluation, agg, ranked))
    add('')
    add('---')
    add('')
    add(
        '<sub>Gerado por `.claude/skills/load-testing` · '
        'thresholds em `references/thresholds.md`</sub>'
    )
    return '\n'.join(lines)


def _conclusion(evaluation, agg, ranked) -> str:
    verdict = evaluation['verdict']
    worst = ranked[0] if ranked else None

    if verdict == PASS:
        text = (
            f"O código atende aos padrões atuais de performance. A aplicação "
            f"sustentou **{agg['rps']:.1f} req/s** com p50 de "
            f"**{agg['p50_ms']:.0f} ms**, p99 de **{agg['p99_ms']:.0f} ms** e "
            f"taxa de erro de **{agg['fail_ratio']:.2%}**, dentro de todos os "
            f'limites definidos.'
        )
    elif verdict == WARN:
        text = (
            f"O código **atende com ressalvas**. Sustentou "
            f"**{agg['rps']:.1f} req/s** (p99 **{agg['p99_ms']:.0f} ms**), mas "
            f'há critérios na faixa de atenção — veja o gate acima. É seguro '
            f'seguir, mas o item sinalizado deve entrar na fila de otimização '
            f'antes que vire regressão.'
        )
    else:
        reasons = '; '.join(
            f"{c['label']} ({c['detail']})"
            for c in evaluation['checks']
            if c['status'] == FAIL
        )
        text = (
            f'O código **não atende** aos padrões atuais de performance. '
            f'Motivos: {reasons}. Recomenda-se corrigir antes do merge/deploy.'
        )

    if worst:
        text += (
            f"\n\n**Gargalo principal**: `{worst['name']}` — p99 "
            f"{worst['p99_ms']:.0f} ms, p95 {worst['p95_ms']:.0f} ms, "
            f"máx {worst['max_ms']:.0f} ms. Comece a investigação por aqui "
            f'(queries da view, serialização, template).'
        )
    return text


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv-prefix', required=True)
    parser.add_argument('--baseline')
    parser.add_argument('--output', required=True)
    parser.add_argument('--json-output')
    parser.add_argument('--scenario', default='baseline')
    parser.add_argument('--host', default='')
    parser.add_argument('--users', default='')
    parser.add_argument('--spawn-rate', default='')
    parser.add_argument('--run-time', default='')
    parser.add_argument('--tags', default='')
    parser.add_argument('--commit', default='')
    parser.add_argument('--branch', default='')
    parser.add_argument(
        '--server-config',
        default=os.getenv('LOADTEST_SERVER_CONFIG', '(não informado)'),
    )
    parser.add_argument(
        '--project',
        default=os.getenv('LOADTEST_PROJECT_NAME') or Path.cwd().name,
        help='Nome do projeto no título do relatório.',
    )
    parser.add_argument(
        '--update-baseline',
        action='store_true',
        help='Grava este resultado como novo baseline (só se não reprovar).',
    )
    args = parser.parse_args()

    csv_prefix = Path(args.csv_prefix)
    stats = read_stats(csv_prefix)
    failures = read_failures(csv_prefix)
    peak_rps, peak_users = read_peak_rps(csv_prefix)

    baseline = None
    baseline_path = Path(args.baseline) if args.baseline else None
    if baseline_path and baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
        if baseline.get('scenario') and baseline['scenario'] != args.scenario:
            print(
                f"AVISO: baseline é do cenário '{baseline['scenario']}', "
                f"rodando '{args.scenario}' — comparação ignorada.",
                file=sys.stderr,
            )
            baseline = None

    evaluation = evaluate(stats, baseline)

    meta = {
        'timestamp': datetime.now(timezone.utc)
        .astimezone()
        .strftime('%Y-%m-%d %H:%M:%S %Z'),
        'scenario': args.scenario,
        'host': args.host or '(não informado)',
        'users': args.users or '?',
        'spawn_rate': args.spawn_rate or '?',
        'run_time': args.run_time or '?',
        'tags': args.tags,
        'commit': args.commit or '(não informado)',
        'branch': args.branch or '(não informado)',
        'server_config': args.server_config,
        'project': args.project,
    }

    report = render_report(
        stats, evaluation, meta, failures, peak_rps, peak_users
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding='utf-8')

    result = {
        'meta': meta,
        'verdict': evaluation['verdict'],
        'aggregated': stats['aggregated'],
        'peak_rps': peak_rps,
        'peak_users': peak_users,
        'endpoints': stats['endpoints'],
        'checks': evaluation['checks'],
        'scenario': args.scenario,
    }
    json_output = Path(args.json_output or output.parent / 'result.json')
    json_output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8'
    )

    print(report)
    print(f'\nRelatório: {output}\nJSON: {json_output}', file=sys.stderr)

    if args.update_baseline and baseline_path:
        if evaluation['verdict'] == FAIL:
            print(
                'Baseline NÃO atualizado: o run reprovou no gate.', file=sys.stderr
            )
        else:
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8'
            )
            print(f'Baseline atualizado: {baseline_path}', file=sys.stderr)

    return 1 if evaluation['verdict'] == FAIL else 0


if __name__ == '__main__':
    raise SystemExit(main())
