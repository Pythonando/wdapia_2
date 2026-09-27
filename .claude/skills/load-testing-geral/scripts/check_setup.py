#!/usr/bin/env python3
"""Verifica se a skill já foi configurada para o projeto atual.

Exit code: 0 = tudo pronto; 1 = falta configurar algo (lista o que).

Checagens (só stdlib, não importa Django nem Locust):

  1. locustfile.py declara ao menos uma classe de usuário com ao menos uma
     `@task` (análise por AST — comentário, docstring e import não contam).
  2. seed_load_test_users.py tem `SEED_CONFIGURED = True`.
  3. loadtest.env tem `LOADTEST_ENV_CONFIGURED=1`.

Quem escreve/configura é o agente `load-test-runner-geral`; este script só
decide se ainda há o que escrever.

    python3 check_setup.py            # relatório legível
    python3 check_setup.py --quiet    # sem saída, só exit code
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def locustfile_has_tests(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, 'locustfile.py não existe'
    source = path.read_text(encoding='utf-8')
    if not source.strip():
        return False, 'locustfile.py está vazio'
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f'locustfile.py com erro de sintaxe: {exc}'

    def is_task(decorator: ast.expr) -> bool:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, 'id', '')
        return name == 'task'

    user_classes = tasks = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = {getattr(b, 'id', getattr(b, 'attr', '')) for b in node.bases}
            if bases & {'HttpUser', 'User', 'FastHttpUser'}:
                user_classes += 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tasks += any(is_task(d) for d in node.decorator_list)

    if not user_classes:
        return False, 'locustfile.py não declara nenhuma classe de usuário (HttpUser)'
    if not tasks:
        return False, 'locustfile.py não tem nenhuma @task'
    return True, f'{user_classes} classe(s) de usuário, {tasks} task(s)'


def flag_set(path: Path, pattern: str, label: str) -> tuple[bool, str]:
    if not path.exists():
        return False, f'{path.name} não existe'
    if re.search(pattern, path.read_text(encoding='utf-8'), re.MULTILINE):
        return True, label
    return False, f'{path.name} ainda não foi configurado'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    checks = {
        'locustfile': locustfile_has_tests(HERE / 'locustfile.py'),
        'seed': flag_set(
            HERE / 'seed_load_test_users.py',
            r'^SEED_CONFIGURED\s*=\s*True\b',
            'hooks do seed configurados',
        ),
        'env': flag_set(
            HERE / 'loadtest.env',
            r'^LOADTEST_ENV_CONFIGURED\s*=\s*1\b',
            'loadtest.env configurado',
        ),
    }

    ready = all(ok for ok, _ in checks.values())
    if not args.quiet:
        for name, (ok, detail) in checks.items():
            print(f"{'OK      ' if ok else 'PENDENTE'} {name}: {detail}")
        print('PRONTO' if ready else 'CONFIGURAÇÃO PENDENTE')
    return 0 if ready else 1


if __name__ == '__main__':
    sys.exit(main())
