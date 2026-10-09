#!/usr/bin/env bash
exec gunicorn core.wsgi --bind "0.0.0.0:${PORT:-8080}"
