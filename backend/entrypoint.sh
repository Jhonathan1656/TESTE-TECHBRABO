#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput --verbosity 0

if [ "${DEMO_MODE:-false}" = "true" ]; then
  python manage.py seed_demo
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 180 \
  --access-logfile -
