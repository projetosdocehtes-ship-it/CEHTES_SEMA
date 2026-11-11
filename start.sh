#!/bin/bash

echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000 &

echo "Starting Celery worker..."
celery -A nome_do_seu_projeto worker -l info &

echo "Starting Celery beat..."
celery -A nome_do_seu_projeto beat -l info &

wait -n

exit $?
