"""Start a local-only UI demo with its own disposable, fictitious database.

Run: backend/.venv/Scripts/python.exe .document-tools/run_demo.py
The generated login is saved outside the project in the local runtime directory.
No passwords or Django secrets are written to the console or repository.
"""
import os
import argparse
import json
from pathlib import Path
import secrets
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=8000)
parser.add_argument('--ready-file',type=Path)
parser.add_argument('--resume-runtime',type=Path,help='Reuse an existing temporary demo DB and login; do not seed/reset.')
parser.add_argument('--uniform-trial-dir',type=Path,help='Explicit private KV demo bundle; never a production school profile.')
args=parser.parse_args()
if args.uniform_trial_dir:
    trial_root=args.uniform_trial_dir.resolve()
    if not (trial_root/'bundle.json').is_file() or not (trial_root/'model.onnx').is_file():
        parser.error('Prepare the private KV demo bundle first.')
    os.environ['UNIFORM_DEMO_ROOT']=str(trial_root)
else:
    os.environ.pop('UNIFORM_DEMO_ROOT',None)
if not 1024<=args.port<=65535:parser.error('Use an unprivileged TCP port.')
url=f'http://127.0.0.1:{args.port}/'
sys.path.insert(0,str(ROOT/'backend'))
if args.resume_runtime:
    runtime=args.resume_runtime.resolve()
    if runtime.parent != Path(tempfile.gettempdir()).resolve() or not runtime.name.startswith('projectmindx-demo-ui-'):
        parser.error('Resume requires a direct temporary demo directory.')
    if not (runtime/'demo.sqlite3').is_file() or not (runtime/'demo-login.txt').is_file():
        parser.error('Resume requires existing demo.sqlite3 and demo-login.txt.')
    values=dict(line.split(': ',1) for line in (runtime/'demo-login.txt').read_text(encoding='utf-8').splitlines() if ': ' in line)
    password=values.get('Password','')
    if not password or values.get('Username')!='demo_supervisor':
        parser.error('Resume requires a valid local demo login file.')
else:
    runtime=Path(tempfile.mkdtemp(prefix='projectmindx-demo-ui-')).resolve()
    password='Demo!'+secrets.token_urlsafe(24)
os.environ.update(DJANGO_SETTINGS_MODULE='config.settings',DJANGO_DB_PATH=str(runtime/'demo.sqlite3'),
                  DJANGO_SECRET_KEY=secrets.token_urlsafe(48),DJANGO_DEBUG='true',
                  DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,[::1]',QR_ENABLED='false',DEMO_PASSWORD=password)

import django
django.setup()
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone
from school_app.academics.models import Classroom
from school_app.schedules.models import ScheduleRule
from school_app.schedules.services import create_session,open_session
from datetime import time

call_command('prepare_vision_models',verbosity=0)
call_command('migrate',interactive=False,verbosity=0)
if not args.resume_runtime:
    call_command('seed_demo')
day=timezone.localdate()
supervisor=get_user_model().objects.get(username='demo_supervisor')
for classroom in Classroom.objects.filter(code__in=['DEMO10A','DEMO10B']) if not args.resume_runtime else []:
    # This full-day window exists only in this new fictitious demo DB.
    ScheduleRule.objects.update_or_create(classroom=classroom,weekday=day.weekday(),slot='MORNING',
        defaults={'start_time':time(0,0),'close_time':time(23,59,59),'grace_minutes':5,'required_uniform':'SHIRT'})
    session,_=create_session(supervisor,{'class_id':str(classroom.pk),'school_date':str(day),'slot':'MORNING'})
    open_session(supervisor,session.pk,session.version)
credentials=runtime/'demo-login.txt'
credentials.write_text('LOCAL UI DEMO ONLY\nURL: '+url+'\nUsername: demo_supervisor\nPassword: '+password+
    '\nTeacher accounts: demo_teacher_a, demo_teacher_b (same demo password)\nFictitious students only; do not use this login outside the local demo.\n',encoding='utf-8')
if args.ready_file:
    args.ready_file.write_text(json.dumps({'url':url,'credentials':str(credentials),'runtime':str(runtime)}),encoding='utf-8')
print('UI: '+url,flush=True)
print('Demo login file: '+str(credentials),flush=True)
print('Existing demo DB/login preserved; sign in again after restart.' if args.resume_runtime else
      'Two classes and today OPEN sessions are ready. Original workspace DB is unchanged.',flush=True)
call_command('runserver',f'127.0.0.1:{args.port}',use_reloader=False)
