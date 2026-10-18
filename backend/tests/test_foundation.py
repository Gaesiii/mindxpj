"""A01/B01 foundation checks; these do not certify business APIs."""

import uuid

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.http import JsonResponse
from django.urls import path

from school_app.core.enums import Role
from school_app.core.errors import error_response


def csrf_probe(request):
    return JsonResponse({"ok": True})


urlpatterns = [path("csrf-probe", csrf_probe)]


class UserFoundationTests(TestCase):
    def test_uuid_identity_and_password_authentication(self):
        user = get_user_model().objects.create_user(
            username="teacher", password="demo-password", role=Role.HOMEROOM_TEACHER
        )
        self.assertIsInstance(user.pk, uuid.UUID)
        self.assertNotEqual(user.password, "demo-password")
        self.assertTrue(user.check_password("demo-password"))
        self.assertEqual(authenticate(username="teacher", password="demo-password"), user)
        self.assertIsNone(authenticate(username="teacher", password="incorrect"))

    def test_locked_account_cannot_authenticate(self):
        get_user_model().objects.create_user(username="locked", password="demo", is_active=False)
        self.assertIsNone(authenticate(username="locked", password="demo"))

    def test_default_account_has_least_privileged_role(self):
        user = get_user_model().objects.create_user(username="unlinked", password="demo")
        self.assertEqual(user.role, Role.STUDENT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_invalid_role_is_rejected_even_without_form_validation(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user(username="invalid", role="ADMIN")

    def test_duplicate_username_is_rejected(self):
        get_user_model().objects.create_user(username="duplicate")
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user(username="duplicate")

    def test_superuser_flags_do_not_implicitly_grant_business_role(self):
        user = get_user_model().objects.create_superuser(username="operator", password="demo")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, Role.STUDENT)


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class JsonConventionTests(TestCase):
    def test_unknown_api_is_json_with_server_request_id(self):
        response = self.client.get("/api/v1/not-implemented", HTTP_X_REQUEST_ID="untrusted")
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(set(body), {"code", "message", "details", "request_id"})
        self.assertEqual(body["code"], "NOT_FOUND")
        self.assertEqual(str(uuid.UUID(body["request_id"])), body["request_id"])
        self.assertEqual(response.headers["X-Request-ID"], body["request_id"])

    @override_settings(ROOT_URLCONF="tests.test_foundation")
    def test_csrf_is_enforced_and_returns_json(self):
        response = Client(enforce_csrf_checks=True).post(
            "/csrf-probe", data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "CSRF_FAILED")
        self.assertNotIn("reason", response.json()["details"])

    def test_error_helper_preserves_field_details_and_unicode(self):
        request = RequestFactory().get("/api/v1/example")
        request.request_id = str(uuid.uuid4())
        response = error_response(request, "VALIDATION_ERROR", "Dữ liệu chưa hợp lệ", 422,
                                  {"full_name": ["Bắt buộc"]})
        import json
        body = json.loads(response.content)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(body["details"], {"full_name": ["Bắt buộc"]})
        self.assertIn("Dữ liệu", response.content.decode())
