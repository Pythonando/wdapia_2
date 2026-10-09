---
name: django-deploy
description: Prepara o projeto Django para deploy em produção (Railway) — gera o requirements.txt com gunicorn, move DEBUG e SECRET_KEY para o .env, configura CSRF_TRUSTED_ORIGINS, Postgres quando DEBUG=False e arquivos estáticos com WhiteNoise. Use quando o usuário pedir "deploy", "preparar para produção", "subir no Railway", "configurar gunicorn/whitenoise", "colocar em produção".
keywords:
  - deploy
  - produção
  - railway
  - gunicorn
  - whitenoise
  - postgres
  - collectstatic
  - python-decouple
---

# Deploy do projeto Django (Railway)

Deixa o projeto pronto para rodar em produção. Execute os passos **na ordem**; cada um é
idempotente — antes de alterar, verifique se já não está feito e não duplique linhas.

Convenções deste repositório: o virtualenv fica em `venv/` (ative com
`source venv/bin/activate`), o pacote do projeto é `core/` e as configurações estão em
`core/settings.py`.

## 1. Instalar as dependências de produção

```bash
source venv/bin/activate
pip install gunicorn whitenoise python-decouple psycopg2-binary
```

- `gunicorn` — servidor WSGI de produção.
- `whitenoise` — serve os arquivos estáticos pelo próprio Django.
- `python-decouple` — fornece o `config()` usado para ler o `.env`.
- `psycopg2-binary` — driver do Postgres (sem ele o `ENGINE` postgresql não sobe).

## 2. Gerar o requirements.txt (com gunicorn)

- **Se não existir `requirements.txt`**: `pip freeze > requirements.txt`.
- **Se já existir e for curado** (lista só as dependências diretas, menor que o
  `pip freeze`): **não sobrescreva** — o `venv/` pode conter ferramentas de desenvolvimento
  (semgrep, radon, mcp…) que não devem ir para produção. Apenas acrescente os pacotes do
  passo 1 que faltam, com a versão instalada:

  ```bash
  pip freeze | grep -iE '^(gunicorn|whitenoise|python-decouple|psycopg2-binary)=='
  ```

Ao final, confirme que `gunicorn` está no arquivo: `grep -i '^gunicorn' requirements.txt`.

## 3. `.env` com DEBUG e SECRET_KEY

1. Gere uma chave nova (não reaproveite a `django-insecure-...` que está versionada):

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
   ```

2. Crie/atualize o `.env` na raiz (preserve as variáveis que já existirem):

   ```dotenv
   DEBUG=True
   SECRET_KEY=<chave gerada>
   ```

3. Garanta que `.env` está no `.gitignore` e **nunca** faça commit dele. Acrescente as
   chaves, sem valores reais, ao `.env.example`:

   ```dotenv
   DEBUG=True
   SECRET_KEY=
   ```

4. Em `core/settings.py`, leia os valores do `.env`:

   ```python
   from decouple import config

   SECRET_KEY = config('SECRET_KEY')

   DEBUG = config('DEBUG', default=False, cast=bool)
   ```

   `default=False` faz com que um ambiente sem a variável caia no modo seguro. Remova a
   `SECRET_KEY` hardcoded. Se o settings já usa `load_dotenv()`/`os.getenv` para outras
   variáveis, mantenha — os dois convivem.

## 4. CSRF_TRUSTED_ORIGINS e ALLOWED_HOSTS

Em `core/settings.py`:

```python
CSRF_TRUSTED_ORIGINS = ['https://*.railway.app']
```

Com `DEBUG=False` o Django também exige o host em `ALLOWED_HOSTS`, senão responde 400.
Acrescente `'.railway.app'` à lista existente (sem remover os hosts que já estão lá).
Se houver domínio próprio, inclua-o nas duas configurações.

## 5. Banco de dados: SQLite em DEBUG, Postgres em produção

Substitua o bloco `DATABASES` de `core/settings.py` por:

```python
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('PGDATABASE'),
            'USER': config('PGUSER'),
            'PASSWORD': config('PGPASSWORD'),
            'HOST': config('PGHOST'),
            'PORT': config('PGPORT'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }
```

As variáveis `PG*` são expostas pelo serviço Postgres do Railway; no serviço da aplicação
elas precisam ser referenciadas (ex.: `PGHOST=${{Postgres.PGHOST}}`). Não as coloque no
`.env` local — com `DEBUG=True` elas nem são lidas.

## 6. WhiteNoise e collectstatic

1. Em `MIDDLEWARE`, insira o WhiteNoise **imediatamente depois** do
   `django.middleware.security.SecurityMiddleware` (onde quer que ele esteja na lista):

   ```python
   'django.middleware.security.SecurityMiddleware',
   'whitenoise.middleware.WhiteNoiseMiddleware',
   ```

2. Configure os estáticos:

   ```python
   STATIC_URL = 'static/'
   STATIC_ROOT = BASE_DIR / 'staticfiles'

   STORAGES = {
       'default': {
           'BACKEND': 'django.core.files.storage.FileSystemStorage',
       },
       'staticfiles': {
           'BACKEND': (
               'django.contrib.staticfiles.storage.StaticFilesStorage'
               if DEBUG
               else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
           ),
       },
   }
   ```

   O storage com manifest fica só em produção: em desenvolvimento e nos testes ele
   quebraria qualquer `{% static %}` enquanto o `collectstatic` não tivesse sido rodado.

3. Adicione `staticfiles/` ao `.gitignore`.

4. Colete os estáticos:

   ```bash
   python manage.py collectstatic --noinput
   ```

## 7. Comando de start

**Se houver `Dockerfile` na raiz**, o Railway builda por ele e ignora o `Procfile`: o start
é o `CMD`/entrypoint da imagem (neste repositório, `entrypoint.prod.sh`). Confira que ele
roda `migrate` e `collectstatic` em sequência (sem `&`) e sobe o gunicorn com o bind
explícito — sem `--bind` ele escuta só em `127.0.0.1:8000` e o Railway devolve 502:

```bash
exec gunicorn core.wsgi --bind "0.0.0.0:${PORT:-8000}"
```

**Se não houver `Dockerfile`** nem `Procfile` (nem start command configurado no Railway),
crie na raiz:

```procfile
web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn core.wsgi --bind 0.0.0.0:$PORT
```

## 8. Verificação

```bash
python manage.py check
python manage.py test
DEBUG=False SECRET_KEY=x PGDATABASE=x PGUSER=x PGPASSWORD=x PGHOST=x PGPORT=5432 \
  python manage.py check --deploy
gunicorn core.wsgi --check-config
```

- `check` e os testes precisam passar com o `.env` local (`DEBUG=True`).
- `check --deploy` valida o caminho de produção sem conectar no banco; relate os avisos
  de segurança que sobrarem (HSTS, cookies seguros, SSL redirect) em vez de ignorá-los.
- Se algum passo falhar, corrija antes de seguir — não reporte o deploy como pronto.

## Variáveis a configurar no Railway

| Variável | Valor |
| --- | --- |
| `DEBUG` | `False` |
| `SECRET_KEY` | chave própria de produção (diferente da local) |
| `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT` | referências ao serviço Postgres |

## Ao terminar

- Informe ao usuário o que foi alterado e as variáveis que ele precisa definir no Railway.
- Como houve alteração de código, rode o agente `doc-sync-onboarding` (obrigatório pelo
  `CLAUDE.md` do projeto) para atualizar a documentação.
- Não faça commit nem push sem o usuário pedir.
