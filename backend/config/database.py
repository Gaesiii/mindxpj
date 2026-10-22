"""Use shared PostgreSQL when configured; explicit SQLite paths isolate builds."""
from urllib.parse import parse_qs, unquote, urlsplit
from django.core.exceptions import ImproperlyConfigured


def database_config(env, sqlite_default):
    if env.get('DJANGO_DB_PATH') or not env.get('DATABASE_URL'):
        return {'ENGINE': 'django.db.backends.sqlite3',
                'NAME': env.get('DJANGO_DB_PATH') or str(sqlite_default), 'OPTIONS': {'timeout': 20}}
    try:
        url = urlsplit(env['DATABASE_URL'])
        query = parse_qs(url.query)
        ssl = query.get('sslmode', ['require'])[0]
        if (url.scheme not in ('postgres', 'postgresql') or not url.hostname or
                not url.username or not url.password or not url.path.strip('/') or
                ssl not in ('require', 'verify-ca', 'verify-full')):
            raise ValueError
        return {'ENGINE': 'django.db.backends.postgresql', 'NAME': unquote(url.path.lstrip('/')),
                'USER': unquote(url.username), 'PASSWORD': unquote(url.password),
                'HOST': url.hostname, 'PORT': url.port or 5432,
                'CONN_MAX_AGE': 0, 'DISABLE_SERVER_SIDE_CURSORS': True,
                'OPTIONS': {'sslmode': ssl, 'connect_timeout': 15, 'prepare_threshold': None}}
    except (ValueError, TypeError):
        raise ImproperlyConfigured('DATABASE_URL must be a valid TLS PostgreSQL connection URL.') from None
