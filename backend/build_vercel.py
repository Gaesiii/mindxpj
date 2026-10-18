"""Create a fresh fictional template, without touching a developer database."""
import os
from pathlib import Path
import tempfile


def main():
    if not os.environ.get('DJANGO_SECRET_KEY') or not os.environ.get('DEMO_PASSWORD'):
        raise SystemExit('Build requires DJANGO_SECRET_KEY and DEMO_PASSWORD environment variables.')
    backend = Path(__file__).resolve().parent
    target = backend / '.vercel-demo' / 'template.sqlite3'
    if target.resolve().parent.parent != backend.resolve():
        raise SystemExit('Invalid demo template target.')
    target.parent.mkdir(exist_ok=True)
    descriptor, staging = tempfile.mkstemp(dir=target.parent, suffix='.sqlite3')
    os.close(descriptor)
    os.environ['DJANGO_DB_PATH'] = staging
    os.environ['VERCEL'] = '1'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    connections = None
    try:
        import django
        django.setup()
        from django.core.management import call_command
        from django.db import connections
        from config.vercel_demo import prepare_demo_rules, refresh_demo_sessions
        call_command('migrate', interactive=False, verbosity=0)
        call_command('seed_demo', verbosity=0)
        prepare_demo_rules()
        refresh_demo_sessions()
        call_command('collectstatic', interactive=False, verbosity=0)
        connections.close_all()
        os.replace(staging, target)
        print('Vercel demo template and static assets prepared; runtime storage is temporary per instance.')
    finally:
        if connections is not None:
            connections.close_all()
        Path(staging).unlink(missing_ok=True)


if __name__ == '__main__':
    main()
