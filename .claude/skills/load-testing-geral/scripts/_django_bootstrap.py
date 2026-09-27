"""Inicializa o Django a partir de qualquer projeto, sem hardcode.

Usado por `seed_load_test_users.py` e `list_routes.py`. Resolve:

* a raiz do repositório (a skill fica em `<raiz>/.claude/skills/<skill>/scripts/`);
* o módulo de settings: `DJANGO_SETTINGS_MODULE` do ambiente, ou, se ausente, o
  default declarado em `manage.py`;
* o `sys.path`: a raiz, `apps/` e `src/` (se existirem) e o que estiver em
  `LOADTEST_EXTRA_PYTHONPATH` (caminhos relativos à raiz, separados por `:`).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

_SETTINGS_RE = re.compile(
    r"""setdefault\(\s*['"]DJANGO_SETTINGS_MODULE['"]\s*,\s*['"]([^'"]+)['"]"""
)


def _settings_from_manage_py() -> str | None:
    manage = PROJECT_ROOT / 'manage.py'
    if not manage.exists():
        return None
    match = _SETTINGS_RE.search(manage.read_text(encoding='utf-8'))
    return match.group(1) if match else None


def setup_django() -> None:
    extra = [
        PROJECT_ROOT / part
        for part in os.getenv('LOADTEST_EXTRA_PYTHONPATH', '').split(':')
        if part
    ]
    candidates = [PROJECT_ROOT, PROJECT_ROOT / 'apps', PROJECT_ROOT / 'src', *extra]
    for path in reversed(candidates):
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))

    if not os.getenv('DJANGO_SETTINGS_MODULE'):
        module = _settings_from_manage_py()
        if not module:
            raise SystemExit(
                'ERRO: defina DJANGO_SETTINGS_MODULE (não foi possível lê-lo '
                'do manage.py).'
            )
        os.environ['DJANGO_SETTINGS_MODULE'] = module

    import django

    django.setup()
