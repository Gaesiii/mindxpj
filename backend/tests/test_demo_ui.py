from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import Client, TestCase, override_settings


class DemoUiTests(TestCase):
    @override_settings(VISION_ENROLLMENT_TOTAL_BYTES=3*1024*1024)
    def test_shell_advertises_runtime_upload_budget(self):
        response = self.client.get('/')
        self.assertContains(response, 'data-enrollment-limit="3145728"')
        self.assertContains(response, 'Tổng ≤3 MiB.')

    def test_public_shell_bootstraps_csrf_without_private_data(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Điểm danh')
        self.assertContains(response,'csrfmiddlewaretoken')
        self.assertContains(response,'demo_ui/app.js')
        self.assertIn('csrftoken',response.cookies)
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertNotContains(response,'Demo!')

    def test_script_and_styles_are_local_assets(self):
        for name in ('demo_ui/app.js','demo_ui/app.css'):
            path=finders.find(name)
            self.assertIsNotNone(path,name)
            self.assertGreater(Path(path).stat().st_size,100)

    def test_shell_does_not_grant_staff_api_or_bypass_csrf(self):
        secure=Client(enforce_csrf_checks=True)
        secure.get('/')
        self.assertEqual(secure.get('/api/v1/classes').status_code,401)
        self.assertEqual(secure.post('/api/v1/auth/login',{'username':'nobody','password':'no'}).status_code,403)
        user=get_user_model().objects.create_user(username='ui_student',role='STUDENT')
        secure.force_login(user)
        self.assertEqual(secure.get('/api/v1/classes').status_code,403)
        self.assertEqual(secure.get('/api/v1/reports/summary',{'date_from':'2026-10-18','date_to':'2026-10-18'}).status_code,403)

    def test_unknown_api_stays_json_and_ui_has_no_secret(self):
        self.assertEqual(self.client.get('/api/v1/ui-missing').json()['code'],'NOT_FOUND')
        response=self.client.get('/')
        self.assertNotContains(response,settings.SECRET_KEY)
