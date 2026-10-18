"""B02/B03 payload validation only; session ORM/API acceptance awaits B04–B06."""
from django.test import SimpleTestCase

from school_app.schedules import forms


class SchedulePayloadTests(SimpleTestCase):
    def rule(self, **changes):
        return {"weekday": 0, "slot": "MORNING", "start_time": "07:00:00",
                "close_time": "08:00:00", "grace_minutes": 5,
                "required_uniform": "SHIRT", **changes}

    def form(self, name, data, **kwargs):
        form_class = getattr(forms, name, None)
        self.assertTrue(callable(form_class), f"{name} has not been implemented")
        return form_class(data, **kwargs)

    def test_morning_shirt_and_afternoon_sports(self):
        for payload in [self.rule(), self.rule(slot="AFTERNOON", start_time="13:00:00",
                                              close_time="14:00:00", required_uniform="SPORTS")]:
            with self.subTest(payload=payload):
                form = self.form("ScheduleRuleForm", payload)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["weekday"], 0)
                self.assertEqual(form.cleaned_data["required_uniform"], payload["required_uniform"])

    def test_all_python_weekdays_valid(self):
        for weekday in range(7):
            self.assertTrue(self.form("ScheduleRuleForm", self.rule(weekday=weekday)).is_valid())

    def test_weekday_rejects_out_of_range_and_non_integer_json(self):
        for weekday in [-1, 7, True, 1.5, "0", None, [0]]:
            with self.subTest(weekday=weekday):
                self.assertFalse(self.form("ScheduleRuleForm", self.rule(weekday=weekday)).is_valid())

    def test_grace_rejects_negative_boolean_fraction_and_string(self):
        for grace in [-1, True, 1.5, "5", None, [5]]:
            with self.subTest(grace=grace):
                self.assertFalse(self.form("ScheduleRuleForm", self.rule(grace_minutes=grace)).is_valid())

    def test_cutoff_equal_to_close_valid_but_after_close_invalid(self):
        self.assertTrue(self.form("ScheduleRuleForm", self.rule(grace_minutes=60)).is_valid())
        self.assertFalse(self.form("ScheduleRuleForm", self.rule(grace_minutes=61)).is_valid())
        self.assertFalse(self.form("ScheduleRuleForm", self.rule(grace_minutes=10**100)).is_valid())

    def test_same_time_or_overnight_session_invalid(self):
        for start, close in [("07:00:00", "07:00:00"), ("23:00:00", "01:00:00")]:
            self.assertFalse(self.form("ScheduleRuleForm", self.rule(start_time=start, close_time=close)).is_valid())

    def test_only_local_time_strings(self):
        for value in ["25:00:00", "07:00:00Z", "07:00:00+07:00", True, ["07:00:00"], "07:00"]:
            self.assertFalse(self.form("ScheduleRuleForm", self.rule(start_time=value)).is_valid())

    def test_slot_and_uniform_choices(self):
        for changes in [{"slot": "EVENING"}, {"required_uniform": "OTHER"},
                        {"slot": ["MORNING"]}, {"required_uniform": True}]:
            self.assertFalse(self.form("ScheduleRuleForm", self.rule(**changes)).is_valid())

    def test_missing_fields_and_extra_identity_are_not_ignored(self):
        for name in self.rule():
            payload = self.rule()
            del payload[name]
            self.assertFalse(self.form("ScheduleRuleForm", payload).is_valid())
        for name in ["class_id", "classroom_id", "actor", "version", "uniform_type"]:
            self.assertFalse(self.form("ScheduleRuleForm", self.rule(**{name: "fake"})).is_valid())

    def test_patch_merges_then_validates_entire_rule(self):
        form = self.form("ScheduleRuleForm", {"close_time": "07:04:00"}, current=self.rule())
        self.assertFalse(form.is_valid())
        form = self.form("ScheduleRuleForm", {"required_uniform": "SPORTS"}, current=self.rule())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["start_time"].hour, 7)
        self.assertEqual(form.cleaned_data["required_uniform"], "SPORTS")

    def test_patch_unknown_fields_rejected_and_original_not_mutated(self):
        current = self.rule()
        self.assertFalse(self.form("ScheduleRuleForm", {"class_id": "fake"}, current=current).is_valid())
        self.assertEqual(current, self.rule())

    def test_session_date_class_and_slot(self):
        payload = {"class_id": "00000000-0000-4000-8000-000000000010",
                   "school_date": "2026-10-12", "slot": "MORNING"}
        form = self.form("SessionCreateForm", payload)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["school_date"].weekday(), 0)
        for changes in [{"class_id": "not-uuid"}, {"class_id": True},
                        {"school_date": "2026-02-30"}, {"school_date": "12/10/2026"},
                        {"slot": "EVENING"}, {"student_id": "fake"}, {"status": "OPEN"}]:
            self.assertFalse(self.form("SessionCreateForm", {**payload, **changes}).is_valid())

    def test_version_requires_non_negative_json_integer(self):
        for value in [0, 1, 100]:
            self.assertTrue(self.form("SessionVersionForm", {"expected_version": value}).is_valid())
        for payload in [{}, {"expected_version": -1}, {"expected_version": True},
                        {"expected_version": "0"}, {"expected_version": 0.5},
                        {"expected_version": 0, "actor": "fake"}]:
            self.assertFalse(self.form("SessionVersionForm", payload).is_valid())

    def test_session_date_invalid_json_types_return_errors_instead_of_crashing(self):
        for value in [True, 0, 1.5, ["2026-10-12"], {"date": "2026-10-12"}, None]:
            with self.subTest(value=value):
                form = self.form("SessionCreateForm", {
                    "class_id": "00000000-0000-4000-8000-000000000010",
                    "school_date": value, "slot": "MORNING"})
                self.assertFalse(form.is_valid())

    def test_session_class_id_requires_canonical_uuid(self):
        for value in ["00000000000040008000000000000010",
                      "{00000000-0000-4000-8000-000000000010}",
                      "urn:uuid:00000000-0000-4000-8000-000000000010"]:
            self.assertFalse(self.form("SessionCreateForm", {
                "class_id": value, "school_date": "2026-10-12", "slot": "MORNING"}).is_valid())
