import json
from datetime import date
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from school_app.academics.models import Classroom, Grade
from school_app.students.models import Student
from school_app.core.enums import Role
from school_app.core.models import ChangeLog
from school_app.schedules.models import Session, SessionRoster

@override_settings(ALLOWED_HOSTS=['testserver'])
class ClassStudentCrudTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.supervisor = users.objects.create_user(username='s',role=Role.SUPERVISOR)
        self.teacher = users.objects.create_user(username='t',role=Role.HOMEROOM_TEACHER)
        self.other = users.objects.create_user(username='o',role=Role.HOMEROOM_TEACHER)
        self.grade = Grade.objects.create(code='10',name='10')
        self.a = Classroom.objects.create(code='A',name='A',grade=self.grade,teacher=self.teacher)
        self.b = Classroom.objects.create(code='B',name='B',grade=self.grade,teacher=self.other)
        self.student = Student.objects.create(student_code='S1',full_name='One',classroom=self.a)
        self.client.force_login(self.supervisor)
    def write(self, method, url, data):
        return getattr(self.client,method)(url,json.dumps(data),content_type='application/json')
    def cu(self, row=None): return '/api/v1/classes/'+str((row or self.a).pk)
    def su(self): return '/api/v1/students/'+str(self.student.pk)
    def test_counts_detail_scope_and_strict_capacity(self):
        result = self.client.get(self.cu())
        self.assertEqual(result.status_code,200)
        self.assertEqual({k:result.json()[k] for k in ('capacity','active','version','active_student_count','total_student_count')},dict(capacity=50,active=True,version=0,active_student_count=1,total_student_count=1))
        for value in (0,51,True,'20',None):
            self.assertEqual(self.write('patch',self.cu(),{'capacity':value,'expected_version':0}).status_code,422)
        self.assertEqual(self.write('patch',self.cu(),{'student_count':2,'expected_version':0}).status_code,422)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.cu(self.b)).status_code,404)
        self.assertEqual(self.write('delete',self.cu(),{'expected_version':0}).status_code,403)
    def test_version_required_and_stale_rejected_without_mutation(self):
        for url,field in ((self.cu(),'name'),(self.su(),'full_name')):
            self.assertEqual(self.write('patch',url,{field:'New'}).status_code,422)
            self.assertEqual(self.write('patch',url,{field:'New','expected_version':0}).status_code,200)
            self.assertEqual(self.write('patch',url,{field:'Stale','expected_version':0}).status_code,409)
            self.assertEqual(self.client.get(url).json()['version'],1)
        self.assertEqual(ChangeLog.objects.filter(action='UPDATE').count(),2)
    def test_capacity_create_transfer_activate_and_archive_restore(self):
        self.assertEqual(self.write('patch',self.cu(),{'capacity':1,'expected_version':0}).status_code,200)
        body={'student_code':'S2','full_name':'Two','class_id':str(self.a.pk)}
        self.assertEqual(self.write('post','/api/v1/students',body).status_code,409)
        other=Student.objects.create(student_code='S3',full_name='Three',classroom=self.b)
        self.assertEqual(self.write('patch','/api/v1/students/'+str(other.pk),{'class_id':str(self.a.pk),'expected_version':0}).status_code,409)
        self.assertEqual(self.write('delete',self.cu(),{'expected_version':1}).status_code,409)
        self.assertEqual(self.write('delete',self.su(),{'expected_version':0}).status_code,200)
        self.assertEqual(self.write('delete',self.cu(),{'expected_version':1}).status_code,200)
        self.assertEqual(self.write('patch',self.su(),{'active':True,'expected_version':1}).status_code,409)
        self.assertEqual(self.write('patch',self.cu(),{'active':True,'expected_version':2}).status_code,200)
        self.assertEqual(self.write('patch',self.su(),{'active':True,'expected_version':1}).status_code,200)
        self.assertEqual(self.write('patch',self.cu(),{'capacity':0,'expected_version':3}).status_code,422)
    def test_teacher_code_transfer_restricted_and_history_retained(self):
        session=Session.objects.create(classroom=self.a,school_date=date(2026,1,1),slot='MORNING')
        roster=SessionRoster.objects.create(session=session,student=self.student,student_code_snapshot='S1',full_name_snapshot='One',class_code_snapshot='A',class_name_snapshot='A',grade_code_snapshot='10',grade_name_snapshot='10')
        self.client.force_login(self.teacher)
        for change in ({'student_code':'NEW'},{'class_id':str(self.b.pk)}):
            self.assertEqual(self.write('patch',self.su(),{**change,'expected_version':0}).status_code,403)
        self.assertEqual(self.write('delete',self.su(),{'expected_version':0}).status_code,200)
        roster.refresh_from_db()
        self.assertEqual(roster.full_name_snapshot,'One')
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())
        self.assertEqual(self.client.get(self.su()).status_code,200)
        self.client.force_login(self.supervisor)
        self.assertEqual(self.write('patch',self.su(),{'student_code':'NEW','expected_version':1}).status_code,200)
        self.assertEqual(self.write('post','/api/v1/students',{'student_code':'NEW','full_name':'Duplicate','class_id':str(self.b.pk)}).status_code,409)
    def test_archive_open_session_and_capacity_reduction_are_conflicts(self):
        Student.objects.create(student_code='S2',full_name='Two',classroom=self.a)
        self.assertEqual(self.write('patch',self.cu(),{'capacity':1,'expected_version':0}).status_code,409)
        Student.objects.filter(classroom=self.a).update(active=False)
        from django.utils import timezone
        Session.objects.create(classroom=self.a,school_date=date(2026,1,2),slot='MORNING',status='OPEN',start_at=timezone.now(),late_cutoff_at=timezone.now(),close_at=timezone.now(),required_uniform_snapshot='ANY')
        self.assertEqual(self.write('delete',self.cu(),{'expected_version':0}).status_code,409)
    def test_selectors_duplicate_codes_and_archive_counts(self):
        self.assertEqual(self.client.get('/api/v1/teachers').status_code,200)
        self.assertEqual({row['id'] for row in self.client.get('/api/v1/teachers').json()['items']},{str(self.teacher.pk),str(self.other.pk)})
        self.assertEqual(self.write('patch',self.cu(),{'code':'B','expected_version':0}).status_code,409)
        self.assertEqual(self.write('delete',self.su(),{'expected_version':False}).status_code,422)
        self.assertEqual(self.write('delete',self.su(),{'expected_version':0,'active':False}).status_code,422)
        self.assertEqual(self.write('delete',self.su(),{'expected_version':0}).status_code,200)
        row=self.client.get(self.cu()).json()
        self.assertEqual((row['active_student_count'],row['total_student_count']),(0,1))
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get('/api/v1/teachers').status_code,403)
    def test_transfer_and_deactivate_invalidate_pending_scans_and_preserve_snapshot(self):
        from school_app.vision.models import VisionScan
        from django.utils import timezone
        from datetime import timedelta
        session=Session.objects.create(classroom=self.a,school_date=date(2026,1,1),slot='MORNING')
        roster=SessionRoster.objects.create(session=session,student=self.student,student_code_snapshot='S1',full_name_snapshot='One',class_code_snapshot='A',class_name_snapshot='A',grade_code_snapshot='10',grade_name_snapshot='10')
        def scan():
            return VisionScan.objects.create(roster=roster,created_by=self.teacher,scanned_at=timezone.now(),expires_at=timezone.now()+timedelta(minutes=1),sample_revision='x',attendance_version=0,distance=0,observed_uniform='UNKNOWN',color_coverage=0)
        first=scan()
        self.assertEqual(self.write('patch',self.su(),{'class_id':str(self.b.pk),'expected_version':0}).status_code,200)
        first.refresh_from_db()
        self.assertEqual((first.status,first.version),('SUPERSEDED',1))
        second=scan()
        self.assertEqual(self.write('delete',self.su(),{'expected_version':1}).status_code,200)
        second.refresh_from_db()
        self.assertEqual(second.status,'SUPERSEDED')
        roster.refresh_from_db()
        self.assertEqual((roster.class_code_snapshot,roster.full_name_snapshot),('A','One'))
    def test_archived_class_rejects_photo_write(self):
        from tests.test_students import picture
        self.student.active=False
        self.student.save()
        self.assertEqual(self.write('delete',self.cu(),{'expected_version':0}).status_code,200)
        self.assertEqual(self.client.post(self.su()+'/photo',{'photo':picture()}).status_code,409)
