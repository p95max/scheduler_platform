#!/bin/sh

set -e

echo "Waiting for PostgreSQL..."

until pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL is ready"

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

echo "Creating superuser (if not exists)..."
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.getenv('DJANGO_SUPERUSER_USERNAME')
email = os.getenv('DJANGO_SUPERUSER_EMAIL') or ''
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

if username and password:
    qs = User.objects.filter(username=username)
    if not qs.exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print('Superuser created',)
    else:
        print('Superuser already exists:', username)
else:
    print('Superuser env vars not set, skipping.')
"

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 120