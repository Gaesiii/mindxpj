"""Create a fresh fictional template, without touching a developer database."""
import os
from pathlib import Path
import tempfile


def main():
    required = ('DJANGO_SECRET_KEY', 'DEMO_PASSWORD')
    missing = [name for name in required if not os.environ.get(name)]
    # Print presence only; never include secret values in public build logs.
    context = f"environment={os.environ.get('VERCEL_ENV', 'local')} commit={os.environ.get('VERCEL_GIT_COMMIT_SHA', 'local')[:12]}"
    presence = ' '.join(name + ('=missing' if name in missing else '=set') for name in required)
    print(f'[demo-build:v2] {context} {presence}', flush=True)
    if missing:
        raise SystemExit('Missing build variables: ' + ', '.join(missing) +
                         '. Add them to the matching Vercel project environment, Save, then create a new deployment. '
                         'Local .env.vercel is not loaded on Vercel.')
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
        from school_app.management_app.management.commands.seed_demo import validate_demo_password
        validate_demo_password(os.environ['DEMO_PASSWORD'])
        print('[demo-build:v2] Demo password checks passed for all 23 accounts.', flush=True)
        call_command('prepare_vision_models', verbosity=0)
        call_command('migrate', interactive=False, verbosity=0)
        call_command('seed_demo', verbosity=0)
        prepare_demo_rules()
        refresh_demo_sessions()
        call_command('collectstatic', interactive=False, verbosity=0)
        connections.close_all()
        os.replace(staging, target)
        print('Isolated SQLite template and static assets prepared. Runtime uses shared PostgreSQL when DATABASE_URL is set; otherwise instance-local SQLite.')
    finally:
        if connections is not None:
            connections.close_all()
        Path(staging).unlink(missing_ok=True)


if __name__ == '__main__':
    main()
