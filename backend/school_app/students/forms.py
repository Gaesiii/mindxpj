from django import forms
from school_app.academics.forms import StrictForm, JsonUUIDField


class StudentCreateForm(StrictForm):
    student_code = forms.CharField(max_length=30)
    full_name = forms.CharField(max_length=150)
    class_id = JsonUUIDField()
    scalar_types = {"student_code": str, "full_name": str, "class_id": str}


class StudentUpdateForm(StrictForm):
    full_name = forms.CharField(max_length=150)
    active = forms.BooleanField(required=False)
    class_id = JsonUUIDField()
    scalar_types = {"full_name": str, "active": bool, "class_id": str}
