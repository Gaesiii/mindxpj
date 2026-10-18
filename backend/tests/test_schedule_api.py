from django.apps import apps
from django.test import SimpleTestCase


class BackendSchemaTests(SimpleTestCase):
    def test_session_roster_and_attendance_schema_is_available(self):
        self.assertIsNotNone(apps.get_app_config('schedules').models.get('session'))
        self.assertIsNotNone(apps.get_app_config('schedules').models.get('sessionroster'))
        self.assertIsNotNone(apps.get_app_config('attendance').models.get('attendance'))
        self.assertIsNotNone(apps.get_app_config('qr').models.get('qrscan'))


from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from school_app.academics.models import Grade, Classroom
from school_app.students.models import Student
from school_app.schedules.models import ScheduleRule, Session, SessionRoster
from school_app.attendance.models import Attendance
from datetime import time, timedelta
import json

class WorkflowCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(username='teacher', role='HOMEROOM_TEACHER')
        self.other = User.objects.create_user(username='other', role='HOMEROOM_TEACHER')
        self.supervisor = User.objects.create_user(username='supervisor', role='SUPERVISOR')
        self.grade = Grade.objects.create(code='G10', name='Grade 10')
        self.classroom = Classroom.objects.create(code='10A', name='Class A', grade=self.grade, teacher=self.teacher)
        self.other_class = Classroom.objects.create(code='10B', name='Class B', grade=self.grade, teacher=self.other)
        self.student = Student.objects.create(student_code='S01', full_name='Student One', classroom=self.classroom)
        self.second = Student.objects.create(student_code='S02', full_name='Student Two', classroom=self.classroom)
        self.student_user = User.objects.create_user(username='student',role='STUDENT',student=self.student)
        self.second_user = User.objects.create_user(username='second',role='STUDENT',student=self.second)
        self.day = timezone.localdate()
        self.rule = ScheduleRule.objects.create(classroom=self.classroom, weekday=self.day.weekday(), slot='MORNING', start_time=time(7), close_time=time(8), grace_minutes=5,required_uniform='SHIRT')
        self.session = Session.objects.create(classroom=self.classroom,school_date=self.day,slot='MORNING')
        self.client.force_login(self.teacher)

    def request(self, method, path, body=None, key=None):
        headers = {'HTTP_IDEMPOTENCY_KEY':key} if key else {}
        return getattr(self.client,method)('/api/v1'+path, data=json.dumps(body if body is not None else {}), content_type='application/json', **headers)

    def open(self):
        result=self.request('post', f'/sessions/{self.session.pk}/open',{'expected_version':0})
        self.assertEqual(result.status_code,200,result.content)
        self.session.refresh_from_db()
        self.attendance=Attendance.objects.get(roster__session=self.session,roster__student=self.student)
        return result

class ScheduleApiTests(WorkflowCase):
    def test_open_atomic_snapshot_and_retry(self):
        result=self.open()
        self.assertEqual(result.json()['version'],1)
        self.assertEqual(SessionRoster.objects.filter(session=self.session).count(),2)
        self.assertEqual(Attendance.objects.filter(roster__session=self.session,status='UNMARKED').count(),2)
        self.student.full_name='Changed'; self.student.save()
        self.rule.required_uniform='SPORTS'; self.rule.save()
        again=self.request('post',f'/sessions/{self.session.pk}/open',{'expected_version':0})
        self.assertEqual(again.status_code,200)
        self.assertEqual(self.session.roster.get(student=self.student).full_name_snapshot,'Student One')
        self.session.refresh_from_db(); self.assertEqual(self.session.required_uniform_snapshot,'SHIRT')

    def test_create_retry_scope_and_duplicate_rule(self):
        body={'class_id':str(self.classroom.id),'school_date':str(self.day),'slot':'MORNING'}
        response=self.request('post','/sessions',body)
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(Session.objects.count(),1)
        response=self.request('post',f'/classes/{self.classroom.pk}/schedule-rules',{'weekday':self.day.weekday(),'slot':'MORNING','start_time':'07:00:00','close_time':'08:00:00','grace_minutes':5,'required_uniform':'SHIRT'})
        self.assertEqual(response.status_code,409,response.content)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/api/v1/sessions/{self.session.pk}').status_code,404)
        self.assertEqual(self.client.get('/api/v1/sessions',{'class_id':str(self.classroom.pk)}).status_code,403)

    def test_stale_open_and_close_preserve_not_checked(self):
        self.assertEqual(self.request('post',f'/sessions/{self.session.pk}/open',{'expected_version':4}).status_code,409)
        self.open()
        self.attendance.status='PRESENT'; self.attendance.source='MANUAL'; self.attendance.arrived_at=timezone.now(); self.attendance.uniform_status='NOT_CHECKED'; self.attendance.save()
        response=self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['converted_unmarked'],1)
        self.assertEqual(response.json()['remaining_not_checked'],1)
        again=self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.assertEqual(again.status_code,200)
        self.attendance.refresh_from_db(); self.assertEqual(self.attendance.uniform_status,'NOT_CHECKED')

    def test_open_rollback_injected_attendance_failure(self):
        from unittest.mock import patch
        with patch('school_app.attendance.models.Attendance.objects.bulk_create',side_effect=RuntimeError('injected')):
            with self.assertRaises(RuntimeError):
                self.request('post',f'/sessions/{self.session.pk}/open',{'expected_version':0})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status,'PLANNED')
        self.assertEqual(self.session.version,0)
        self.assertEqual(self.session.roster.count(),0)


    def test_existing_create_retry_does_not_need_changed_rule(self):
        self.rule.weekday=(self.day.weekday()+1)%7;self.rule.save()
        response=self.request('post','/sessions',{'class_id':str(self.classroom.pk),'school_date':str(self.day),'slot':'MORNING'})
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(Session.objects.count(),1)

    def test_open_only_active_roster_and_invalid_filters(self):
        self.second.active=False;self.second.save()
        self.open()
        self.assertEqual(self.session.roster.count(),1)
        for params in [{'date_from':'bad'},{'date_from':'2026-10-15','date_to':'2026-10-14'},{'slot':'NIGHT'},{'role':'SUPERVISOR'}]:
            self.assertEqual(self.client.get('/api/v1/sessions',params).status_code,422)
        self.client.force_login(self.student_user)
        self.assertEqual(self.client.get('/api/v1/sessions').status_code,403)

    def test_rule_partial_patch_preserves_cutoff_and_snapshot(self):
        response=self.request('patch',f'/schedule-rules/{self.rule.pk}',{'close_time':'07:04:00'})
        self.assertEqual(response.status_code,422,response.content)
        self.open()
        response=self.request('patch',f'/schedule-rules/{self.rule.pk}',{'required_uniform':'SPORTS'})
        self.assertEqual(response.status_code,200,response.content)
        self.session.refresh_from_db();self.assertEqual(self.session.required_uniform_snapshot,'SHIRT')

    def test_planned_close_and_missing_rule_open_rejected(self):
        self.assertEqual(self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':0}).status_code,409)
        self.rule.delete()
        response=self.request('post',f'/sessions/{self.session.pk}/open',{'expected_version':0})
        self.assertEqual(response.status_code,422,response.content)
        self.session.refresh_from_db();self.assertEqual(self.session.status,'PLANNED')
        self.assertEqual(self.session.roster.count(),0)
