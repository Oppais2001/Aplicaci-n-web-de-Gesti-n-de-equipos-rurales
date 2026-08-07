pip install -r requirements.txt

python manage.py migrate

python manage.py collectstatic --noinput

python manage.py loaddata datos.json || true

python manage.py createsuperuser --noinput || true