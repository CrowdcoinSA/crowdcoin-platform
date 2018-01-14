web: gunicorn crowdcoincoza.wsgi --preload --log-file -
worker: celery  -A website.tasks.app worker -B --loglevel=info