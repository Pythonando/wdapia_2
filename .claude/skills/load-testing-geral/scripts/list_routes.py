#!/usr/bin/env python
"""Lista todas as rotas do projeto Django (padrão, nome e view).

Ponto de partida para escrever o locustfile: mostra o que existe, e você lê as
views para saber método aceito, autenticação e se a rota tem efeito colateral.

    python .claude/skills/load-testing-geral/scripts/list_routes.py
    python .../list_routes.py --filter pedidos
"""

from __future__ import annotations

import argparse

from _django_bootstrap import setup_django

setup_django()

from django.urls import URLPattern, URLResolver, get_resolver  # noqa: E402


def walk(patterns, prefix=''):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from walk(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            callback = entry.callback
            view = getattr(callback, '__module__', '?') + '.' + getattr(
                callback, '__qualname__', getattr(callback, '__name__', '?')
            )
            yield prefix + str(entry.pattern), entry.name or '-', view


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='', help='Só rotas que contenham o texto.')
    args = parser.parse_args()

    rows = sorted(set(walk(get_resolver().url_patterns)))
    for route, name, view in rows:
        if args.filter in route or args.filter in view:
            print(f'/{route}\t{name}\t{view}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
