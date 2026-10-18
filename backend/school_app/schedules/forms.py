"""B03 JSON payload forms; database/scope validation belongs to B04–B06 services."""
import re

from django import forms
from django.core.exceptions import ValidationError

from school_app.core.enums import RequiredUniform, Slot, Weekday


class JsonIntegerField(forms.IntegerField):
    def to_python(self, value):
        if value is not None and type(value) is not int:
            raise ValidationError("Phải là số nguyên JSON.")
        return super().to_python(value)


class JsonChoiceField(forms.ChoiceField):
    def to_python(self, value):
        if value is not None and not isinstance(value, str):
            raise ValidationError("Phải là chuỗi JSON.")
        return super().to_python(value)


class LocalTimeField(forms.TimeField):
    def to_python(self, value):
        if value is not None and (not isinstance(value, str) or
                                  not re.fullmatch(r"\d{2}:\d{2}:\d{2}", value)):
            raise ValidationError("Giờ địa phương phải có dạng HH:MM:SS, không timezone.")
        return super().to_python(value)


class StrictPayloadForm(forms.Form):
    """Caller parses JSON object; unknown fields are business validation errors."""
    def clean(self):
        cleaned = super().clean()
        unknown = set(self.data) - set(self.fields)
        if unknown:
            raise ValidationError("Trường không được phép: %(fields)s",
                                  params={"fields": ", ".join(sorted(unknown))})
        return cleaned


class JsonDateField(forms.DateField):
    def to_python(self, value):
        if value is not None and (not isinstance(value, str) or
                                  not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)):
            raise ValidationError("Ngày phải là chuỗi YYYY-MM-DD.")
        return super().to_python(value)


class JsonUUIDField(forms.UUIDField):
    def to_python(self, value):
        if value is not None and (not isinstance(value, str) or not re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value)):
            raise ValidationError("Phải là chuỗi UUID có dấu gạch.")
        return super().to_python(value)


class ScheduleRuleForm(StrictPayloadForm):
    weekday = JsonIntegerField(min_value=min(Weekday.values), max_value=max(Weekday.values))
    slot = JsonChoiceField(choices=Slot.choices)
    start_time = LocalTimeField(input_formats=["%H:%M:%S"])
    close_time = LocalTimeField(input_formats=["%H:%M:%S"])
    grace_minutes = JsonIntegerField(min_value=0)
    required_uniform = JsonChoiceField(choices=RequiredUniform.choices)

    def __init__(self, data=None, *, current=None, **kwargs):
        # PATCH needs all current rule values in serialized JSON form; never
        # validate a partial time policy without its other fields.
        if data is not None and current is not None:
            data = {**current, **data}
        super().__init__(data=data, **kwargs)

    def clean(self):
        cleaned = super().clean()
        start, close = cleaned.get("start_time"), cleaned.get("close_time")
        grace = cleaned.get("grace_minutes")
        if start is not None and close is not None:
            if start >= close:
                self.add_error("close_time", "Giờ đóng phải sau giờ bắt đầu trong cùng ngày.")
            elif grace is not None:
                start_seconds = start.hour * 3600 + start.minute * 60 + start.second
                close_seconds = close.hour * 3600 + close.minute * 60 + close.second
                if start_seconds + grace * 60 > close_seconds:
                    self.add_error("grace_minutes", "Ngưỡng muộn không được sau giờ đóng.")
        return cleaned


class SessionCreateForm(StrictPayloadForm):
    class_id = JsonUUIDField()
    school_date = JsonDateField(input_formats=["%Y-%m-%d"])
    slot = JsonChoiceField(choices=Slot.choices)

class SessionVersionForm(StrictPayloadForm):
    expected_version = JsonIntegerField(min_value=0)
