"""A03 strict scalar forms shared with dependent student forms."""
from django import forms
from school_app.accounts.services import AccountError
from school_app.core.api import parse_uuid


class JsonUUIDField(forms.UUIDField):
    def to_python(self, value):
        if value in self.empty_values:
            return None
        try:
            return parse_uuid(value)
        except AccountError:
            raise forms.ValidationError("Use a dashed UUID string.") from None


class StrictForm(forms.Form):
    scalar_types = {}

    def clean(self):
        cleaned = super().clean()
        for key in self.data:
            if key not in self.fields:
                raise forms.ValidationError("Field is not allowed.")
        for key, scalar_type in self.scalar_types.items():
            if key in self.data and type(self.data[key]) is not scalar_type:
                self.add_error(key, "Invalid JSON field type.")
        return cleaned


class GradeForm(StrictForm):
    code = forms.CharField(max_length=30)
    name = forms.CharField(max_length=100)
    scalar_types = {"code": str, "name": str}


class ClassroomForm(GradeForm):
    grade_id = JsonUUIDField()
    teacher_id = JsonUUIDField()
    scalar_types = {**GradeForm.scalar_types, "grade_id": str, "teacher_id": str}
