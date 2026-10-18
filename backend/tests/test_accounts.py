"""A02 session, input, provisioning and role boundaries; classroom scope awaits A03."""
import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.test import Client, RequestFactory, TestCase, override_settings

from school_app.core.enums import Role

PASSWORD = "Rivers!Purple92"


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class AuthApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {role: get_user_model().objects.create_user(
            username=role.lower(), password=PASSWORD, role=role
        ) for role in Role.values}

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)

    def bootstrap(self):
        response = self.client.get("/api/v1/auth/me")
        self.assertIn("csrftoken", self.client.cookies)
        return response

    def post(self, route, payload, **headers):
        return self.client.post("/api/v1/auth/" + route, json.dumps(payload),
                                content_type="application/json",
                                HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
                                **headers)

    def login(self, role=Role.STUDENT):
        self.bootstrap()
        return self.post("login", {"username": role.lower(), "password": PASSWORD})

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        body = response.json()
        self.assertEqual(body["code"], code)
        self.assertEqual(set(body), {"code", "message", "details", "request_id"})
        self.assertEqual(body["request_id"], response.headers["X-Request-ID"])
        self.assertNotIn(PASSWORD, response.content.decode())

    def test_me_bootstraps_csrf_before_unauthenticated_error(self):
        self.assert_error(self.bootstrap(), 401, "UNAUTHENTICATED")

    def test_three_roles_login_and_me_return_only_safe_identity(self):
        for role, user in self.users.items():
            with self.subTest(role=role):
                self.client = Client(enforce_csrf_checks=True)
                response = self.login(role)
                self.assertEqual(response.status_code, 200)
                expected = {"id": str(user.id), "username": user.username, "role": role,
                            "student_id": None, "class_ids": []}
                self.assertEqual(response.json(), expected)
                self.assertEqual(self.client.get("/api/v1/auth/me").json(), expected)
                self.assertNotIn(user.password, response.content.decode())
                self.assertTrue(self.client.cookies["sessionid"]["httponly"])

    def test_login_rotates_existing_session_and_csrf(self):
        session = self.client.session
        session["old_marker"] = "previous browser session"
        session.save()
        old_key = session.session_key
        self.bootstrap()
        old_csrf = self.client.cookies["csrftoken"].value
        response = self.post("login", {"username": "student", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old_key, self.client.cookies["sessionid"].value)
        self.assertNotEqual(old_csrf, self.client.cookies["csrftoken"].value)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        self.assertNotIn("old_marker", self.client.session)

    def test_login_missing_and_wrong_csrf_are_json_forbidden(self):
        for token in (None, "x" * 32):
            self.bootstrap()
            headers = {} if token is None else {"HTTP_X_CSRFTOKEN": token}
            response = self.client.post("/api/v1/auth/login",
                                        json.dumps({"username": "student", "password": PASSWORD}),
                                        content_type="application/json", **headers)
            self.assert_error(response, 403, "CSRF_FAILED")

    def test_logout_missing_wrong_and_prelogin_csrf_preserve_session(self):
        self.bootstrap()
        old_csrf = self.client.cookies["csrftoken"].value
        self.assertEqual(self.login().status_code, 200)
        for token in (None, "x" * 32, old_csrf):
            headers = {} if token is None else {"HTTP_X_CSRFTOKEN": token}
            response = self.client.post("/api/v1/auth/logout", "{}",
                                        content_type="application/json", **headers)
            self.assert_error(response, 403, "CSRF_FAILED")
            self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)

    def test_logout_flushes_session_and_old_cookie_cannot_authenticate(self):
        self.assertEqual(self.login().status_code, 200)
        old_key = self.client.cookies["sessionid"].value
        response = self.post("logout", {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        replay = Client()
        replay.cookies["sessionid"] = old_key
        self.assert_error(replay.get("/api/v1/auth/me"), 401, "UNAUTHENTICATED")

    def test_inactive_user_loses_existing_session_access(self):
        self.assertEqual(self.login().status_code, 200)
        get_user_model().objects.filter(pk=self.users[Role.STUDENT].pk).update(is_active=False)
        self.assert_error(self.client.get("/api/v1/auth/me"), 401, "UNAUTHENTICATED")
        self.assert_error(self.post("logout", {}), 401, "UNAUTHENTICATED")

    def test_wrong_unknown_and_inactive_credentials_share_generic_error(self):
        get_user_model().objects.create_user(username="locked", password=PASSWORD, is_active=False)
        self.bootstrap()
        messages = []
        for username, password in (("student", "wrong"), ("missing", PASSWORD), ("locked", PASSWORD)):
            response = self.post("login", {"username": username, "password": password})
            self.assert_error(response, 401, "INVALID_CREDENTIALS")
            messages.append(response.json()["message"])
        self.assertEqual(len(set(messages)), 1)

    def test_login_rejects_extra_fields_and_wrong_types(self):
        self.bootstrap()
        for payload in ({}, [], None, "text", {"username": 2, "password": PASSWORD},
                        {"username": True, "password": PASSWORD},
                        {"username": "student", "password": [PASSWORD]},
                        {"username": "student", "password": " "},
                        *({"username": "student", "password": PASSWORD, key: "injected"}
                          for key in ("role", "student_id", "student_user_id", "is_staff", "actor"))):
            with self.subTest(payload=payload):
                self.assert_error(self.post("login", payload), 422, "VALIDATION_ERROR")

    def test_login_rejects_malformed_json_and_encoding(self):
        self.bootstrap()
        for payload in (b"{", b'\xff'):
            response = self.client.post("/api/v1/auth/login", payload, content_type="application/json",
                                        HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)
            self.assert_error(response, 400, "BAD_REQUEST")

    def test_login_rejects_escaped_lone_surrogates_before_encoding_or_database(self):
        self.bootstrap()
        for payload in ({"username": "\ud800", "password": PASSWORD},
                        {"username": "student", "password": "\udfff"},
                        {"username": "student", "password": PASSWORD, "\ud800": "value"}):
            self.assert_error(self.post("login", payload), 400, "BAD_REQUEST")

    def test_logout_rejects_identity_injection(self):
        self.login()
        self.assert_error(self.post("logout", {"student_id": "other"}), 422, "VALIDATION_ERROR")
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)

    def test_no_public_registration_or_wrong_method(self):
        for route in ("register", "signup"):
            self.assert_error(self.client.get("/api/v1/auth/" + route), 404, "NOT_FOUND")
        response = self.client.get("/api/v1/auth/login")
        self.assert_error(response, 405, "METHOD_NOT_ALLOWED")
        self.assertEqual(response.headers["Allow"], "POST")

    @patch("school_app.accounts.services.time.time", return_value=1_700_000_000)
    def test_login_is_rate_limited_even_if_usernames_change(self, _clock):
        from school_app.accounts.services import LOGIN_ATTEMPTS
        self.bootstrap()
        for index in range(LOGIN_ATTEMPTS):
            self.assert_error(self.post("login", {"username": f"unknown{index}", "password": PASSWORD}),
                              401, "INVALID_CREDENTIALS")
        response = self.post("login", {"username": "student", "password": PASSWORD},
                             HTTP_X_FORWARDED_FOR="different")
        self.assert_error(response, 429, "RATE_LIMITED")
        self.assertGreater(int(response.headers["Retry-After"]), 0)


class ProvisionAndPermissionTests(TestCase):
    def test_provision_hashes_validates_and_defaults_to_student(self):
        from school_app.accounts.services import provision_user
        user = provision_user(username="new-pupil", password=PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)
        self.assertEqual(user.role, Role.STUDENT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_provision_rejects_duplicate_role_weak_password_and_invalid_username(self):
        from school_app.accounts.services import provision_user
        provision_user(username="new-pupil", password=PASSWORD)
        for args in ({"username": "new-pupil", "password": PASSWORD},
                     {"username": "bad-role", "password": PASSWORD, "role": "ADMIN"},
                     {"username": "weak", "password": "123"},
                     {"username": "whitespace", "password": " " * 20},
                     {"username": 12, "password": PASSWORD},
                     {"username": "bad name", "password": PASSWORD}):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                provision_user(**args)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_provision_supports_explicit_business_roles(self):
        from school_app.accounts.services import provision_user
        for role in Role.values:
            self.assertEqual(provision_user(username=role.lower(), password=PASSWORD, role=role).role, role)

    def test_permission_helpers_require_active_user_explicit_role_and_link(self):
        from school_app.accounts.permissions import require_authenticated, require_roles, require_student
        from school_app.accounts.services import AccountError
        from django.contrib.auth.models import AnonymousUser
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        with self.assertRaises(AccountError) as caught:
            require_authenticated(request)
        self.assertEqual(caught.exception.code, "UNAUTHENTICATED")
        request.user = get_user_model().objects.create_superuser(username="operator", password=PASSWORD)
        with self.assertRaises(AccountError) as caught:
            require_roles(request, Role.SUPERVISOR)
        self.assertEqual(caught.exception.code, "FORBIDDEN")
        request.student_id = "forged identity"
        with self.assertRaises(AccountError) as caught:
            require_student(request)
        self.assertEqual(caught.exception.code, "STUDENT_NOT_LINKED")
        request.user.role = Role.SUPERVISOR
        self.assertEqual(require_roles(request, Role.SUPERVISOR), request.user)
        with self.assertRaises(AccountError) as caught:
            require_student(request)
        self.assertEqual(caught.exception.code, "FORBIDDEN")
        request.user.is_active = False
        with self.assertRaises(AccountError) as caught:
            require_authenticated(request)
        self.assertEqual(caught.exception.code, "UNAUTHENTICATED")

    def test_command_prompts_password_and_prints_no_secret(self):
        output = StringIO()
        with patch("school_app.accounts.management.commands.provision_user.getpass",
                   side_effect=[PASSWORD, PASSWORD]):
            call_command("provision_user", "command-pupil", stdout=output)
        user = get_user_model().objects.get(username="command-pupil")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotIn(PASSWORD, output.getvalue())
        self.assertNotIn(user.password, output.getvalue())

    def test_command_has_no_password_argument_and_mismatch_creates_nothing(self):
        with self.assertRaises(CommandError):
            call_command("provision_user", "pupil", "--password", PASSWORD)
        with patch("school_app.accounts.management.commands.provision_user.getpass", side_effect=[PASSWORD, "other"]):
            with self.assertRaises(CommandError):
                call_command("provision_user", "pupil")
        self.assertFalse(get_user_model().objects.exists())
