"""Reproduce checks, non-destructive migration, CSRF HTTP demo and export evidence.

Run from project root with backend/.venv/Scripts/python.exe. All DBs are temporary;
only fictitious report artifacts and a log are retained. No biometric frame saved.
"""
import csv
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, time, timedelta
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
OUT = ROOT / 'docs/project-management/evidence'
SAMPLES = OUT / 'sface-upgrade' / 'synthetic-exports'
LOG = []


def note(message):
    LOG.append(message)
    print(message, flush=True)


def command(args):
    result = subprocess.run([sys.executable,*args], cwd=BACKEND, env=os.environ.copy(),
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    LOG.extend(['\nCOMMAND: '+ ' '.join(args), result.stdout, result.stderr, f'EXIT: {result.returncode}'])
    print(f"{' '.join(args)}: exit {result.returncode}",flush=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def upgrade_and_demo():
    import django
    django.setup()
    from django.db import connection, connections
    from django.db.migrations.executor import MigrationExecutor
    from django.core.management import call_command
    from django.utils import timezone

    executor = MigrationExecutor(connection)
    targets = [('attendance','0002_initial') if app=='attendance' else (app,name)
               for app,name in executor.loader.graph.leaf_nodes() if app!='vision']
    executor.migrate(targets)
    old = executor.loader.project_state(targets).apps
    User, Grade, Classroom, Student, Session, Roster, Attendance, Challenge, Scan = [old.get_model(app,model) for app,model in (
        ('accounts','User'),('academics','Grade'),('academics','Classroom'),('students','Student'),
        ('schedules','Session'),('schedules','SessionRoster'),('attendance','Attendance'),('qr','QrChallenge'),('qr','QrScan'))]
    now=timezone.now()
    teacher=User.objects.create(username='legacy_teacher',role='HOMEROOM_TEACHER')
    grade=Grade.objects.create(code='legacy',name='Legacy')
    classroom=Classroom.objects.create(code='legacy',name='Legacy',grade=grade,teacher=teacher)
    student=Student.objects.create(student_code='legacy',full_name='Legacy fictional pupil',classroom=classroom)
    pupil=User.objects.create(username='legacy_pupil',role='STUDENT',student=student)
    session=Session.objects.create(classroom=classroom,school_date=timezone.localdate(),slot='MORNING',status='OPEN',
        start_at=now,late_cutoff_at=now,close_at=now+timedelta(hours=1),required_uniform_snapshot='SHIRT')
    roster=Roster.objects.create(session=session,student=student,student_code_snapshot='legacy',full_name_snapshot='Legacy',
        class_code_snapshot='legacy',class_name_snapshot='Legacy',grade_code_snapshot='legacy',grade_name_snapshot='Legacy')
    attendance=Attendance.objects.create(roster=roster,status='PRESENT',source='QR',arrived_at=now,uniform_status='NOT_CHECKED')
    challenge=Challenge.objects.create(session=session,token_hash='a'*64,issued_by=teacher,issued_at=now,expires_at=now+timedelta(seconds=60))
    scan=Scan.objects.create(roster=roster,challenge=challenge,student_user=pupil,scanned_at=now,
        expires_at=now+timedelta(minutes=15),status='CONFIRMED',resolved_by=teacher,resolved_at=now)
    saved=(attendance.pk,scan.pk,student.pk)
    call_command('migrate',interactive=False,stdout=io.StringIO(),verbosity=0)
    from school_app.attendance.models import Attendance
    from school_app.qr.models import QrScan
    from school_app.students.models import Student
    from school_app.vision.models import FaceSample
    assert Attendance.objects.get(pk=saved[0]).source=='QR'
    assert QrScan.objects.get(pk=saved[1]).status=='CONFIRMED'
    assert Student.objects.filter(pk=saved[2]).exists() and FaceSample.objects.count()==0
    note('Upgrade v1.2 -> v1.3: legacy student, QR confirmation and QR attendance preserved.')

    from django.contrib.auth import get_user_model
    from django.test import Client
    from school_app.academics.models import Grade, Classroom
    from school_app.schedules.models import ScheduleRule, Session, SessionRoster
    from school_app.core.models import ChangeLog
    from tests.test_vision_engine import BOX, frame, upload
    from tests.test_vision_api import VisionApiTests
    import cv2
    from openpyxl import load_workbook

    User=get_user_model(); password=secrets.token_urlsafe(24)
    teacher=User.objects.create_user(username='vision_demo_teacher',password=password,role='HOMEROOM_TEACHER')
    other=User.objects.create_user(username='vision_other_teacher',role='HOMEROOM_TEACHER')
    grade=Grade.objects.create(code='VISION10',name='Khối demo')
    classroom=Classroom.objects.create(code='VISION10A',name='Lớp demo OpenCV',grade=grade,teacher=teacher)
    pupils=[Student.objects.create(student_code=f'VISION{i}',full_name=f'Học sinh giả {i}',classroom=classroom) for i in range(1,4)]
    pupil_user=User.objects.create_user(username='vision_demo_pupil',role='STUDENT',student=pupils[0])
    day=timezone.localdate()
    clock_value=timezone.make_aware(datetime.combine(day,time(7,4)))
    ScheduleRule.objects.create(classroom=classroom,weekday=day.weekday(),slot='MORNING',start_time=time(7),
        close_time=time(8),grace_minutes=5,required_uniform='SHIRT')
    client=Client(enforce_csrf_checks=True)
    filters={'date_from':str(day),'date_to':str(day),'class_id':str(classroom.pk)}

    def write(method,path,payload,key=None):
        headers={'HTTP_X_CSRFTOKEN':client.cookies['csrftoken'].value}
        if key:
            headers['HTTP_IDEMPOTENCY_KEY']=key
        result=getattr(client,method)('/api/v1'+path,data=json.dumps(payload),content_type='application/json',**headers)
        assert result.status_code in (200,201), result.content
        return result.json()

    with patch('django.utils.timezone.now',return_value=clock_value) as clock, \
         patch('school_app.vision.engine.extract_face',side_effect=lambda image:(cv2.resize(image[50:170,200:320],(112,112)),BOX)), \
         patch('school_app.vision.engine.embed_face',side_effect=VisionApiTests.synthetic_embedding):
        assert client.get('/api/v1/auth/me').status_code==401
        write('post','/auth/login',{'username':teacher.username,'password':password})
        session=write('post','/sessions',{'class_id':str(classroom.pk),'school_date':str(day),'slot':'MORNING'})
        base=f"/sessions/{session['id']}"
        write('post',base+'/open',{'expected_version':0})
        url=f'/api/v1/students/{pupils[0].pk}/face-samples'
        result=client.post(url,{'images':[upload(frame(i)) for i in (1,2,3)]},HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        assert result.status_code==201,result.content
        result=client.post('/api/v1'+base+'/vision-scans',{'image':upload()},HTTP_IDEMPOTENCY_KEY='vision-demo-analysis',
                           HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        assert result.status_code==201,result.content
        candidate=result.json()['scan']
        summary=client.get('/api/v1/reports/summary',filters).json()
        assert (summary['present'],summary['unmarked'])==(0,3)
        path=f"/vision-scans/{candidate['id']}/confirm"
        payload={'identity_confirmed':True,'expected_scan_version':0,'expected_attendance_version':0,
                 'uniform':{'observed_uniform':'SHIRT','uniform_status':'COMPLIANT'}}
        confirmed=write('post',path,payload,'vision-demo-confirm')
        logs=ChangeLog.objects.count()
        assert write('post',path,payload,'vision-demo-confirm')==confirmed
        assert logs==ChangeLog.objects.count()
        assert confirmed['attendance']['source']=='VISION'
        assert confirmed['attendance']['arrived_at']==candidate['scanned_at']
        clock.return_value=clock_value+timedelta(minutes=6)
        second=Attendance.objects.get(roster__session_id=session['id'],roster__student=pupils[1])
        write('patch',f'/attendance/{second.pk}',{'expected_version':0,'status':'PRESENT',
            'arrived_at':(clock_value+timedelta(minutes=5)).isoformat(),'reason':'Demo manual fallback'},'vision-demo-manual')
        write('patch',f'/attendance/{second.pk}/uniform',{'expected_version':1,'observed_uniform':'SPORTS',
            'uniform_status':'NON_COMPLIANT','reason':'Buổi yêu cầu sơ mi'},'vision-demo-uniform')
        write('post',base+'/close',{'expected_version':1})
        details=client.get('/api/v1/reports/attendance',filters).json()
        summary=client.get('/api/v1/reports/summary',filters).json()
        expected={'expected':3,'present':2,'absent':1,'unmarked':0,'on_time':1,'late':1,'compliant':1,'non_compliant':1,'not_checked':0}
        assert {name:summary[name] for name in expected}==expected
        vision=next(row for row in details['items'] if row['source']=='VISION')
        assert vision['scanned_at']==vision['arrived_at']
        SAMPLES.mkdir(parents=True,exist_ok=True)
        for kind in ('xlsx','csv'):
            result=client.get('/api/v1/reports/export',{**filters,'format':kind})
            assert result.status_code==200,result.content
            data=result.content
            if kind=='xlsx':
                book=load_workbook(io.BytesIO(data))
                assert dict(book['Tong_hop'].values)==summary
                headers=list(next(book['Chi_tiet'].values))
                rows=[dict(zip(headers,row)) for row in list(book['Chi_tiet'].values)[1:]]
            else:
                rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
            assert len(rows)==3
            for column,value,count in (
                ('Nguồn','VISION',1),('Nguồn','MANUAL',1),
                ('Trạng thái','PRESENT',2),('Trạng thái','ABSENT',1),('Trạng thái','UNMARKED',0),
                ('Đúng giờ/muộn','ON_TIME',1),('Đúng giờ/muộn','LATE',1),
                ('Kết quả đồng phục','COMPLIANT',1),('Kết quả đồng phục','NON_COMPLIANT',1),
                ('Kết quả đồng phục','NOT_CHECKED',0)):
                assert sum(row[column]==value for row in rows)==count, (kind,column,value)
            exported=next(row for row in rows if row['Nguồn']=='VISION')
            assert exported['Giờ quét']==exported['Giờ đến']
            assert sum(row['Trạng thái']=='PRESENT' for row in rows)==summary['present']
            (SAMPLES/f'attendance-vision-demo.{kind}').write_bytes(data)
        negative=Client(enforce_csrf_checks=True)
        negative.force_login(other)
        assert negative.get(url).status_code==404
        assert negative.get('/api/v1'+base+'/vision-scans').status_code==404
        negative.force_login(pupil_user)
        assert negative.get('/api/v1/reports/export',{**filters,'format':'csv'}).status_code==403
        write('post','/auth/logout',{})
        assert client.get('/api/v1'+base+'/vision-scans').status_code==401
        (SAMPLES/'summary-vision-demo.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        (SAMPLES/'detail-vision-demo.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
        note('CSRF HTTP: login -> enroll -> analyze(PENDING, 0 present) -> confirm -> retry -> manual -> uniform -> close -> report/export: PASS')
        note('Exports reopened: 3 roster, 2 present, 1 absent; 1 VISION/1 MANUAL; 1 on time/1 late; 1 compliant/1 non-compliant: PASS')
        note('Wrong-class teacher, student export and logged-out access blocked: PASS')
    connections.close_all()


def main():
    sys.path.insert(0,str(BACKEND))
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings',DJANGO_SECRET_KEY=secrets.token_urlsafe(48),
                      DJANGO_DEBUG='false',DJANGO_ALLOWED_HOSTS='testserver,localhost,127.0.0.1',PYTHONIOENCODING='utf-8',QR_ENABLED='false')
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='projectmindx-vision-') as folder:
            os.environ['DJANGO_DB_PATH']=str(Path(folder)/'fresh.sqlite3')
            if '--demo-only' not in sys.argv:
                for args in (['manage.py','check'],['manage.py','migrate','--noinput'],
                             ['manage.py','makemigrations','--check','--dry-run'],['-m','pip','check'],
                             ['manage.py','test','--noinput']):
                    command(args)
            os.environ['DJANGO_DB_PATH']=str(Path(folder)/'upgrade.sqlite3')
            upgrade_and_demo()
        note('Temporary DBs cleaned; workspace DB unchanged. Synthetic textured faces; detection/alignment/embedding mocked for synthetic HTTP only. Real cosine matching/HSV run. Real SFace image/browser validation is separate. No camera accuracy/liveness claim.')
    finally:
        target = OUT / 'sface-upgrade'
        target.mkdir(exist_ok=True)
        (target/'legacy-upgrade-validation.txt').write_text('\n'.join(LOG),encoding='utf-8')


if __name__=='__main__':
    main()
