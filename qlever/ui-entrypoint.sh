#!/bin/sh
# Start the QLever UI with its backend already pointed at our QLever instance.
#
# The published image runs gunicorn and nothing else: a fresh install has no
# Backend row, so the UI comes up with nothing to query and the only way to add
# one is through its own admin UI. `manage.py configure` only updates a backend
# that already exists, so seed the row first and then let configure set it as
# the default.
#
# The URL is the one the *browser* uses, not the one this container uses: the UI
# hands it to the page and the page calls the endpoint from wherever you opened
# the UI. A compose service name would resolve in neither.
set -e

python manage.py migrate --noinput

BACKEND_URL="${QLEVER_BACKEND_URL:-http://localhost:8081}"

python manage.py shell -c "
import os
from backend.models import Backend
url = os.environ['QLEVER_BACKEND_URL']
backend, created = Backend.objects.get_or_create(
    slug='entitybase',
    defaults={'name': 'Entitybase'},
)
backend.name = 'Entitybase'
backend.baseUrl = url
backend.isDefault = True
backend.save()
print(('created' if created else 'updated'), 'backend ->', url)
"

# Point everything at the one backend, so the UI does not offer an empty list.
python manage.py configure entitybase "${BACKEND_URL}"

# The port is overridable for the same reason the endpoint's is: with
# --network host there is no port mapping to publish 7000 as 8086, so the UI has
# to serve the port the job asks for itself.
PORT="${QLEVER_UI_PORT:-7000}"

exec gunicorn --bind ":${PORT}" --workers 3 --limit-request-line 10000 qlever.wsgi:application
