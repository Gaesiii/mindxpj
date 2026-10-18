"""A04–A07 current-class scope, private photos and transfer boundaries."""
import json
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from school_app.academics.models import Grade, Classroom
from school_app.students.models import Student
from school_app.core.enums import Role


def picture(name="profile.png", image_format="PNG", exif=False, size=(8, 8)):
    stream = BytesIO()
    image = Image.new("RGB", size, "red")
    kwargs = {}
    if exif:
        metadata = Image.Exif()
        metadata[270] = "private metadata"
        kwargs["exif"] = metadata
    image.save(stream, format=image_format, **kwargs)
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/" + image_format.lower())


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class StudentApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.supervisor = User.objects.create_user(username="supervisor", role=Role.SUPERVISOR)
        self.teacher = User.objects.create_user(username="teacher", role=Role.HOMEROOM_TEACHER)
        self.other = User.objects.create_user(username="other", role=Role.HOMEROOM_TEACHER)
        self.pupil = User.objects.create_user(username="pupil")
        grade = Grade.objects.create(code="10", name="Khối 10")
        self.classroom = Classroom.objects.create(code="10A", name="10A", grade=grade, teacher=self.teacher)
        self.foreign = Classroom.objects.create(code="10B", name="10B", grade=grade, teacher=self.other)
        self.student = Student.objects.create(student_code="HS01", full_name="Nguyễn An", classroom=self.classroom)
        self.another = Student.objects.create(student_code="HS02", full_name="Trần Bình", classroom=self.foreign)
        self.pupil.student = self.student
        self.pupil.save()
        self.client.force_login(self.teacher)
        self.media = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=Path(self.media.name))
        self.settings_override.enable()
        self.addCleanup(self.media.cleanup)
        self.addCleanup(self.settings_override.disable)

    def write(self, method, url, payload):
        return getattr(self.client, method)(url, json.dumps(payload), content_type="application/json")

    def student_url(self, student=None):
        return "/api/v1/students/" + str((student or self.student).id)

    def upload(self, upload=None, student=None):
        return self.client.post(self.student_url(student) + "/photo", {"photo": upload or picture()})

    def test_teacher_list_search_and_explicit_class_filter_use_database_scope(self):
        response = self.client.get("/api/v1/students")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()["items"]], [str(self.student.id)])
        self.assertEqual(len(self.client.get("/api/v1/students", {"search": "Nguyễn"}).json()["items"]), 1)
        self.assertEqual(len(self.client.get("/api/v1/students", {"search": "HS01"}).json()["items"]), 1)
        self.assertEqual(self.client.get("/api/v1/students", {"search": "HS02"}).json()["items"], [])
        self.assertEqual(self.client.get("/api/v1/students", {"class_id": str(self.foreign.id)}).status_code, 403)
        self.assertEqual(self.client.get(self.student_url(self.another)).status_code, 404)

    def test_create_duplicate_name_allowed_duplicate_code_conflict(self):
        payload = {"student_code": "HS03", "full_name": "Nguyễn An", "class_id": str(self.classroom.id)}
        response = self.write("post", "/api/v1/students", payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["grade_id"], str(self.classroom.grade_id))
        self.assertNotIn("photo_path", response.json())
        self.assertEqual(self.write("post", "/api/v1/students", payload).status_code, 409)
        self.assertEqual(self.write("post", "/api/v1/students", {**payload, "student_code": "HS04", "class_id": str(self.foreign.id)}).status_code, 403)

    def test_teacher_updates_profile_and_active_but_only_supervisor_can_transfer(self):
        response = self.write("patch", self.student_url(), {"full_name": "New Name", "active": False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["active"])
        self.assertEqual(self.write("patch", self.student_url(), {"class_id": str(self.foreign.id)}).status_code, 403)
        self.client.force_login(self.supervisor)
        moved = self.write("patch", self.student_url(), {"class_id": str(self.foreign.id)})
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["class_id"], str(self.foreign.id))
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.student_url()).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.student_url()).status_code, 200)

    def test_student_reads_minimal_own_identity_only_and_cannot_list_write_or_photo(self):
        self.client.force_login(self.pupil)
        response = self.client.get(self.student_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"id", "student_code", "full_name", "class_id", "grade_id"})
        self.assertEqual(self.client.get(self.student_url(self.another)).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/students").status_code, 403)
        self.assertEqual(self.write("patch", self.student_url(), {"full_name": "Changed"}).status_code, 403)
        self.assertEqual(self.client.get(self.student_url() + "/photo").status_code, 403)
        self.assertEqual(self.upload().status_code, 403)

    def test_payload_strict_types_allowlist_and_bad_filters(self):
        valid = {"student_code": "HS03", "full_name": "An", "class_id": str(self.classroom.id)}
        for payload in ({**valid, "role": "SUPERVISOR"}, {**valid, "photo_path": "/private"},
                        {**valid, "full_name": 1}, {**valid, "student_code": " "},
                        {**valid, "class_id": True}):
            self.assertEqual(self.write("post", "/api/v1/students", payload).status_code, 422)
        for payload in ({"active": "false"}, {"active": None}, {"student_code": "changed"}, {"student_id": str(self.another.id)}):
            self.assertEqual(self.write("patch", self.student_url(), payload).status_code, 422)
        for query in ({"class_id": "bad"}, {"active": "maybe"}, {"student_id": str(self.another.id)}):
            self.assertEqual(self.client.get("/api/v1/students", query).status_code, 422)

    def test_anonymous_inactive_and_operator_have_no_staff_data_access(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/students").status_code, 401)
        operator = get_user_model().objects.create_superuser(username="operator")
        self.client.force_login(operator)
        self.assertEqual(self.client.get("/api/v1/students").status_code, 403)
        self.client.force_login(self.teacher)
        self.teacher.is_active = False
        self.teacher.save()
        self.assertEqual(self.client.get(self.student_url()).status_code, 401)

    def test_class_reference_ids_require_dashed_uuid_strings(self):
        payload = {"student_code": "HS03", "full_name": "An", "class_id": self.classroom.id.hex}
        self.assertEqual(self.write("post", "/api/v1/students", payload).status_code, 422)
        self.client.force_login(self.supervisor)
        self.assertEqual(self.write("patch", self.student_url(), {"class_id": "urn:uuid:" + str(self.foreign.id)}).status_code, 422)

    def test_duplicate_query_filters_are_rejected(self):
        response = self.client.get("/api/v1/students?class_id=" + str(self.classroom.id) + "&class_id=" + str(self.classroom.id))
        self.assertEqual(response.status_code, 422)

    def test_photo_upload_private_normalized_download_and_reassignment_scope(self):
        response = self.upload(picture("input.jpg", "JPEG", exif=True))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["has_photo"])
        self.assertNotIn("photo_path", response.json())
        self.student.refresh_from_db()
        private_path = Path(self.media.name) / self.student.photo_path
        self.assertTrue(private_path.exists())
        with Image.open(private_path) as normalized:
            self.assertEqual(normalized.format, "PNG")
            self.assertFalse(normalized.getexif())
        download = self.client.get(self.student_url() + "/photo")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download.headers["Content-Type"], "image/png")
        self.assertIn("nosniff", download.headers["X-Content-Type-Options"])
        body = b"".join(download.streaming_content)
        download.close()
        self.assertTrue(body.startswith(b"\x89PNG"))
        self.assertEqual(self.client.get("/private_media/" + self.student.photo_path).status_code, 404)
        self.classroom.teacher = self.other
        self.classroom.save()
        self.assertEqual(self.client.get(self.student_url() + "/photo").status_code, 404)
        self.client.force_login(self.other)
        new_teacher_download = self.client.get(self.student_url() + "/photo")
        self.assertEqual(new_teacher_download.status_code, 200)
        new_teacher_download.close()

    def test_fake_oversize_pixelcap_and_extra_fields_keep_existing_photo(self):
        self.assertEqual(self.upload().status_code, 200)
        self.student.refresh_from_db()
        original_path = self.student.photo_path
        for bad in (SimpleUploadedFile("fake.jpg", b"not a photo", content_type="image/jpeg"),
                    SimpleUploadedFile("big.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png"),
                    picture("bad.gif", "GIF")):
            self.assertEqual(self.upload(bad).status_code, 422)
        with patch("school_app.core.storage.MAX_IMAGE_PIXELS", 100):
            self.assertEqual(self.upload(picture(size=(11, 10))).status_code, 422)
        self.assertEqual(self.client.post(self.student_url() + "/photo", {"photo": picture(), "student_id": str(self.another.id)}).status_code, 422)
        self.student.refresh_from_db()
        self.assertEqual(self.student.photo_path, original_path)
        self.assertTrue((Path(self.media.name) / original_path).exists())
        self.assertEqual(len(list(Path(self.media.name).rglob("*.png"))), 1)

    def test_webp_is_accepted_and_missing_photo_is_not_found(self):
        self.assertEqual(self.client.get(self.student_url() + "/photo").status_code, 404)
        self.assertEqual(self.upload(picture("profile.webp", "WEBP")).status_code, 200)

    def test_photo_replacement_deletes_old_only_after_database_commit(self):
        self.assertEqual(self.upload().status_code, 200)
        self.student.refresh_from_db()
        old_path = Path(self.media.name) / self.student.photo_path
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.upload().status_code, 200)
            self.assertTrue(old_path.exists())
        self.assertFalse(old_path.exists())
        self.assertEqual(len(list(Path(self.media.name).rglob("*.png"))), 1)

    def test_database_failure_during_photo_replace_removes_new_and_preserves_old(self):
        from school_app.students.services import replace_photo
        self.assertEqual(self.upload().status_code, 200)
        self.student.refresh_from_db()
        old_path = self.student.photo_path
        with patch.object(Student, "save", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                replace_photo(self.teacher, self.student.id, picture())
        self.student.refresh_from_db()
        self.assertEqual(self.student.photo_path, old_path)
        self.assertTrue((Path(self.media.name) / old_path).exists())
        self.assertEqual(len(list(Path(self.media.name).rglob("*.png"))), 1)

    def test_committed_photo_replace_succeeds_if_old_file_is_in_use_on_windows(self):
        self.assertEqual(self.upload().status_code, 200)
        self.student.refresh_from_db()
        old_path = self.student.photo_path
        with patch("school_app.students.services.remove_photo", side_effect=PermissionError("file in use")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.upload()
                self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertNotEqual(self.student.photo_path, old_path)
        self.assertTrue((Path(self.media.name) / self.student.photo_path).exists())

    def test_photo_upload_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        response = client.post(self.student_url() + "/photo", {"photo": picture()})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "CSRF_FAILED")
