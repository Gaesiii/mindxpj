from tests.test_schedule_api import WorkflowCase
from django.utils import timezone
from datetime import datetime, time, timedelta
from school_app.core.models import ChangeLog, IdempotencyRequest
from school_app.schedules.models import SessionRoster
from school_app.attendance.models import Attendance

class AttendanceApiTests(WorkflowCase):
    def setUp(self):
        super().setUp(); self.open()
        self.path=f'/attendance/{self.attendance.pk}'

    def manual_body(self, **extra):
        return {'expected_version':0,'status':'PRESENT','arrived_at':(timezone.now()-timedelta(seconds=2)).isoformat(),'reason':'Retrospective entry',**extra}

    def test_manual_retry_conflict_and_scope_before_replay(self):
        body=self.manual_body()
        first=self.request('patch',self.path,body,'manual-key')
        self.assertEqual(first.status_code,200,first.content)
        again=self.request('patch',self.path,body,'manual-key')
        self.assertEqual(again.json(),first.json())
        self.assertEqual(ChangeLog.objects.filter(entity_type='Attendance').count(),1)
        self.assertEqual(self.request('patch',self.path,{**body,'reason':'different'},'manual-key').status_code,409)
        self.classroom.teacher=self.other; self.classroom.save()
        self.assertEqual(self.request('patch',self.path,body,'manual-key').status_code,404)

    def test_manual_validation_and_cutoff_inclusive(self):
        body=self.manual_body()
        for altered in [{'arrived_at':'2026-10-14T07:00:00'},{'arrived_at':(timezone.now()+timedelta(days=1)).isoformat()},{'reason':None},{'status':'UNMARKED'},{'expected_version':True},{'source':'QR'},{'arrived_at':'0001-01-01T00:00:00+14:00'}]:
            response=self.request('patch',self.path,{**body,**altered},'bad-'+str(altered))
            self.assertEqual(response.status_code,422,response.content)
        missing={k:v for k,v in body.items() if k != 'arrived_at'}
        self.assertEqual(self.request('patch',self.path,missing,'missing-arrival').status_code,422)
        # Fixed historical day ensures both cutoff checks are in the past.
        self.session.school_date=timezone.localdate()-timedelta(days=1)
        self.session.start_at=timezone.make_aware(datetime.combine(self.session.school_date,time(7)))
        self.session.late_cutoff_at=self.session.start_at+timedelta(minutes=5)
        self.session.close_at=self.session.start_at+timedelta(hours=1); self.session.save()
        response=self.request('patch',self.path,self.manual_body(arrived_at=self.session.late_cutoff_at.isoformat()),'on-time')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['arrival_status'],'ON_TIME')
        response=self.request('patch',self.path,self.manual_body(expected_version=1,arrived_at=(self.session.late_cutoff_at+timedelta(seconds=1)).isoformat()),'late')
        self.assertEqual(response.json()['arrival_status'],'LATE')
        self.assertTrue(response.json()['arrived_at'].endswith('Z'))

    def test_uniform_closed_teacher_blocked_supervisor_reason(self):
        self.assertEqual(self.request('patch',self.path,self.manual_body(),'present').status_code,200)
        uniform={'expected_version':1,'observed_uniform':'SHIRT','uniform_status':'COMPLIANT'}
        result=self.request('patch',self.path+'/uniform',uniform,'uniform')
        self.assertEqual(result.status_code,200,result.content)
        self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.assertEqual(self.request('patch',self.path,self.manual_body(expected_version=2),'closed').status_code,409)
        # Retry must replay success even after close.
        self.assertEqual(self.request('patch',self.path+'/uniform',uniform,'uniform').status_code,200)
        self.client.force_login(self.supervisor)
        self.assertEqual(self.request('patch',self.path,{'expected_version':2,'status':'ABSENT'},'closed-no-reason').status_code,422)
        response=self.request('patch',self.path,{'expected_version':2,'status':'ABSENT','reason':'Correction'},'closed-reason')
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['uniform_status'],'NOT_APPLICABLE')
        self.assertIsNone(response.json()['source'])

    def test_uniform_failure_does_not_increment_or_log(self):
        self.assertEqual(self.request('patch',self.path,self.manual_body(),'present').status_code,200)
        count=ChangeLog.objects.count()
        response=self.request('patch',self.path+'/uniform',{'expected_version':1,'observed_uniform':'SPORTS','uniform_status':'COMPLIANT'},'bad-uniform')
        self.assertEqual(response.status_code,422,response.content)
        self.attendance.refresh_from_db(); self.assertEqual(self.attendance.version,1)
        self.assertEqual(ChangeLog.objects.count(),count)
        self.assertFalse(IdempotencyRequest.objects.filter(key='bad-uniform').exists())
