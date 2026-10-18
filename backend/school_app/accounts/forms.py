"""Strict auth JSON fields; Django CharField alone coerces scalar values."""
from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)

    def clean_password(self):
        value = self.cleaned_data["password"]
        if not value.strip():
            raise forms.ValidationError("Password is required.")
        return value


def validate_payload(payload, allowed):
    if not isinstance(payload, dict):
        return {"body": ["A JSON object is required."]}
    errors = {key: ["Field is not allowed."] for key in payload if key not in allowed}
    for key in allowed:
        if key not in payload or not isinstance(payload[key], str):
            errors[key] = ["A string is required."]
    return errors
