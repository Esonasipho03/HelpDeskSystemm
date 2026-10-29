#!/usr/bin/env bash
# Render build script: exit on the first error so a failed step fails the deploy loudly.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate --noinput
