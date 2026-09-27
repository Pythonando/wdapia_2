#!/usr/bin/env python
"""Cria/atualiza os usuários (e dados) usados pelo teste de carga.

Idempotente: rodar várias vezes não duplica nada. Roda dentro do container web
(ou com o venv do projeto ativo):

    python .claude/skills/load-testing-geral/scripts/seed_load_test_users.py --count 50
    python .claude/skills/load-testing-geral/scripts/seed_load_test_users.py --purge

O que é genérico (feito aqui): bootstrap do Django, usuários com o campo de
login real do `AUTH_USER_MODEL` (`USERNAME_FIELD`), senha, `is_active`.

O que é específico do projeto (HOOKS abaixo, preenchidos pelo agente
`load-test-runner-geral`):

  * `user_defaults`  — campos obrigatórios extras do model de usuário;
  * `grant_access`   — o que o usuário precisa para passar pelo gate de acesso
                       do app (assinatura, e-mail verificado, onboarding…);
  * `has_access`     — checa se ele realmente passa (o seed aborta se não);
  * `seed_data`      — dados de domínio para listagens/detalhes não virem vazios;
  * `purge_data`     — remove o que não cai em cascata a partir do usuário.

Sem `grant_access` correto, o teste mede o redirect do middleware em vez da
aplicação. Sem `seed_data`, as rotas de detalhe retornam vazio e o resultado é
otimista.
"""

from __future__ import annotations

import argparse
import os

from _django_bootstrap import setup_django

setup_django()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402

User = get_user_model()

# O agente muda para True depois de preencher os hooks. `check_setup.py` lê isto.
SEED_CONFIGURED = False

DEFAULT_COUNT = 50
DEFAULT_PASSWORD = os.getenv('LOADTEST_PASSWORD', 'LoadTest!2024')
# `or` (e não o default do getenv): o compose exporta a variável vazia quando o
# host não a define, e '' é um padrão inválido. Valor do campo de login do
# usuário (e-mail ou username), com `{i}` no lugar do índice.
USER_PATTERN = os.getenv('LOADTEST_USER_PATTERN') or 'loadtest+{i}@example.com'


# --------------------------------------------------------------------------- #
# HOOKS — específicos do projeto
# --------------------------------------------------------------------------- #


def user_defaults(index: int) -> dict:
    """Campos obrigatórios do model de usuário além do login e da senha.

    Ex.: `{'first_name': 'Load', 'accepted_terms': True}`.
    """
    return {}


def grant_access(user) -> bool:
    """Garante que `user` passa pelo gate de acesso do app.

    Retorne True se criou algo (só para o contador). Se o projeto não tem gate
    (middleware/permissão além de estar logado), deixe como está.
    """
    return False


def has_access(user) -> bool:
    """True se `user` passa pelo gate. Use o MESMO critério do middleware."""
    return True


def seed_data(user) -> str:
    """Cria dados de domínio para `user` (idempotente). Retorna um resumo.

    Crie o suficiente para listagens e páginas de detalhe renderizarem conteúdo
    real, e — se houver polling/streaming — ao menos um registro "em andamento".
    """
    return ''


def purge_data(users_qs) -> None:
    """Remove dados semeados que não são apagados em cascata com o usuário."""


# --------------------------------------------------------------------------- #
# Genérico
# --------------------------------------------------------------------------- #


def _identity(index: int) -> str:
    return USER_PATTERN.format(i=index)


@transaction.atomic
def seed(count: int, password: str) -> None:
    field = User.USERNAME_FIELD
    created = updated = granted = 0
    summaries: set[str] = set()

    for index in range(1, count + 1):
        user, was_created = User.objects.get_or_create(
            **{field: _identity(index)},
            defaults={'is_active': True, **user_defaults(index)},
        )
        user.set_password(password)
        user.is_active = True
        user.save()
        granted += bool(grant_access(user))
        created += was_created
        updated += not was_created

        if not has_access(user):
            raise SystemExit(
                f'ERRO: {_identity(index)} não passa pelo gate de acesso após o '
                'seed — o teste inteiro mediria um redirect. Revise '
                '`grant_access`/`has_access`.'
            )
        summary = seed_data(user)
        if summary:
            summaries.add(summary)

    print(f'Usuários de carga prontos: {created} criados, {updated} atualizados.')
    print(f'Acessos concedidos agora: {granted} (gate verificado para todos).')
    for summary in sorted(summaries):
        print(f'Dados semeados: {summary}')


def purge() -> None:
    prefix = USER_PATTERN.split('{i}')[0]
    users = User.objects.filter(**{f'{User.USERNAME_FIELD}__startswith': prefix})
    purge_data(users)
    deleted, _ = users.delete()
    print(f'{deleted} registros removidos (prefixo "{prefix}").')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=DEFAULT_COUNT)
    parser.add_argument('--password', default=DEFAULT_PASSWORD)
    parser.add_argument(
        '--purge',
        action='store_true',
        help='Remove os usuários de carga em vez de criá-los.',
    )
    args = parser.parse_args()

    if args.purge:
        purge()
    else:
        seed(args.count, args.password)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
