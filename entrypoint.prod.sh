#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn core.wsgi --bind "0.0.0.0:${PORT:-8080}"
