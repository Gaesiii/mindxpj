"""Shared runtime storage must not leak into isolated builds or local demos."""
from django.test import SimpleTestCase


class DatabaseConfigTests(SimpleTestCase):
    def test_postgres_connection_and_build_override(self):
        from config.database import database_config
        url = 'postgresql://demo:p%40ss@database.example:5432/demo?sslmode=require'
        pg = database_config({'DATABASE_URL': url}, '/local.sqlite3')
        self.assertEqual(pg['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual((pg['NAME'], pg['USER'], pg['PASSWORD']), ('demo', 'demo', 'p@ss'))
        self.assertEqual(pg['OPTIONS']['sslmode'], 'require')
        self.assertEqual(pg['CONN_MAX_AGE'], 0)
        sqlite = database_config({'DATABASE_URL': url, 'DJANGO_DB_PATH': '/build.sqlite3'}, '/local.sqlite3')
        self.assertEqual(sqlite['ENGINE'], 'django.db.backends.sqlite3')
        self.assertEqual(sqlite['NAME'], '/build.sqlite3')

    def test_invalid_shared_url_fails_closed_without_echoing_credentials(self):
        from config.database import database_config
        from django.core.exceptions import ImproperlyConfigured
        for url in ('sqlite:///tmp/test', 'postgresql://secret@example', 'postgresql://u:secret@host/db?sslmode=disable'):
            with self.subTest(url=url), self.assertRaises(ImproperlyConfigured) as error:
                database_config({'DATABASE_URL': url}, '/local.sqlite3')
            self.assertNotIn('secret', str(error.exception))

    def test_shared_runtime_skips_template_and_only_refreshes_daily_sessions(self):
        from unittest.mock import patch
        from django.test import override_settings
        from config.vercel_demo import DemoBootstrapMiddleware
        import tempfile
        with tempfile.TemporaryDirectory() as directory, override_settings(
                DATABASES={'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'demo'}},
                PRIVATE_MEDIA_ROOT=directory, FILE_UPLOAD_TEMP_DIR=directory), \
                patch('config.vercel_demo.ensure_database') as copy, \
                patch('config.vercel_demo.refresh_shared_demo_sessions') as refresh:
            middleware = DemoBootstrapMiddleware(lambda request: 'response')
            self.assertEqual(middleware(object()), 'response')
            self.assertEqual(middleware(object()), 'response')
            copy.assert_not_called()
            refresh.assert_called_once()
