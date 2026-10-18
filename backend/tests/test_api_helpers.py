"""Shared HTTP behavior exercised by real Django requests, no business mock API."""
import json

from django.db import OperationalError
from django.test import SimpleTestCase, override_settings
from django.urls import path

from school_app.accounts.services import AccountError
from school_app.core import api
from school_app.schedules.forms import SessionVersionForm


def echo(request):
    return api.json_response(api.read_json(request, allowed={"name"}))


def version(request):
    return api.json_response(api.form_data(SessionVersionForm(api.read_json(request))))


def denied(request):
    raise AccountError("FORBIDDEN", "Không có quyền", 403)


def busy(request):
    raise OperationalError("database is locked")


urlpatterns = []


@override_settings(ROOT_URLCONF=__name__, DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ApiHelperTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        global urlpatterns
        decorator = getattr(api, "api_view", None)
        if callable(decorator):
            urlpatterns = [path("echo", decorator("POST")(echo)),
                           path("version", decorator("POST")(version)),
                           path("denied", decorator("GET")(denied)),
                           path("busy", decorator("POST")(busy))]

    def post(self, path, data):
        self.assertTrue(callable(getattr(api, "api_view", None)), "API wrapper missing")
        return self.client.post(path, data=data, content_type="application/json")

    def test_json_unicode_success_no_cache(self):
        response = self.post("/echo", '{"name":"Tiếng Việt"}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"name": "Tiếng Việt"})
        self.assertIn("no-store", response["Cache-Control"])

    def test_bad_json_utf8_and_nonfinite_number(self):
        for data in [b"\xff", b"{", b'{"name":NaN}', b'{"name":Infinity}',
                     b'{"name":1e999}', b'{"name":[-1e999]}']:
            self.assertEqual(self.post("/echo", data).status_code, 400)

    def test_non_object_unknown_field_and_form_errors(self):
        for data in ['[]', 'true', '{"actor":"fake"}']:
            self.assertEqual(self.post("/echo", data).status_code, 422)
        response = self.post("/version", '{"expected_version":true}')
        self.assertEqual(response.status_code, 422)
        self.assertIn("expected_version", response.json()["details"])

    def test_surrogate_strings_rejected_recursively(self):
        for data in [r'{"\ud800":"value"}', r'{"name":"\ud800"}',
                     r'{"name":[{"value":"\udfff"}]}']:
            self.assertEqual(self.post("/echo", data).status_code, 400)

    def test_method_error_is_json_with_allow_header(self):
        self.assertTrue(callable(getattr(api, "api_view", None)))
        response = self.client.get("/echo")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "POST")
        self.assertEqual(response.json()["code"], "METHOD_NOT_ALLOWED")

    def test_business_error_and_database_busy(self):
        self.assertTrue(callable(getattr(api, "api_view", None)))
        response = self.client.get("/denied")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["request_id"], response["X-Request-ID"])
        response = self.post("/busy", '{}')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "DATABASE_BUSY")

    def test_uuid_requires_dashed_string(self):
        parser = getattr(api, "parse_uuid", None)
        self.assertTrue(callable(parser))
        self.assertEqual(str(parser("00000000-0000-4000-8000-000000000010")),
                         "00000000-0000-4000-8000-000000000010")
        for value in [True, "00000000000040008000000000000010", "fake"]:
            with self.assertRaises(AccountError):
                parser(value)
