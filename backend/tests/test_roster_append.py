from school_app.schedules.models import SessionRoster
from school_app.students.models import Student
from tests.test_schedule_api import WorkflowCase


class RosterAppendTests(WorkflowCase):
    def setUp(self):
        super().setUp()
        self.open()
        self.new = Student.objects.create(student_code='NEW', full_name='New pupil', classroom=self.classroom)
        self.url = f'/sessions/{self.session.pk}/roster'
        self.body = {'expected_session_version':1, 'student_id':str(self.new.pk)}

    def test_supervisor_append_preserves_snapshot_and_idempotency(self):
        self.client.force_login(self.supervisor)
        response = self.request('post',self.url,self.body,'append')
        self.assertEqual(response.status_code,201,response.content)
        self.assertEqual(self.request('post',self.url,self.body,'append').json(),response.json())
        self.assertEqual(SessionRoster.objects.filter(session=self.session).count(),3)
        self.assertEqual(self.session.roster.get(student=self.student).full_name_snapshot,'Student One')
        self.assertEqual(self.session.roster.get(student=self.new).attendance.status,'UNMARKED')
        self.session.refresh_from_db()
        self.assertEqual(self.session.version,2)

    def test_teacher_cannot_append_and_closed_or_wrong_class_rejected(self):
        self.assertEqual(self.request('post',self.url,self.body,'teacher').status_code,403)
        self.client.force_login(self.supervisor)
        self.new.classroom=self.other_class
        self.new.save()
        self.assertEqual(self.request('post',self.url,self.body,'wrong-class').status_code,409)
        self.request('post',f'/sessions/{self.session.pk}/close',{'expected_version':1})
        self.assertEqual(self.request('post',self.url,self.body,'closed').status_code,409)
