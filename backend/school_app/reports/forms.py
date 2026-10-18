"""Strict report query parameters; no silent ignored or repeated filters."""
import re
from django import forms
from school_app.accounts.services import AccountError
from school_app.core.api import form_data, parse_uuid
from school_app.core.enums import Slot, AttendanceStatus


class IsoDateField(forms.DateField):
    def to_python(self, value):
        if value and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise forms.ValidationError('Use YYYY-MM-DD.')
        return super().to_python(value)


class ReportFilterForm(forms.Form):
    date_from = IsoDateField(input_formats=['%Y-%m-%d'])
    date_to = IsoDateField(input_formats=['%Y-%m-%d'])
    class_id = forms.CharField(required=False)
    grade_id = forms.CharField(required=False)
    slot = forms.ChoiceField(choices=Slot.choices, required=False)
    status = forms.ChoiceField(choices=AttendanceStatus.choices, required=False)

    def clean(self):
        values = super().clean()
        if values.get('date_from') and values.get('date_to') and values['date_from'] > values['date_to']:
            self.add_error('date_to', 'Must be on or after date_from.')
        for name in ('class_id', 'grade_id'):
            if values.get(name):
                values[name] = parse_uuid(values[name])
        return values


def read_filters(query, *, export=False):
    allowed = set(ReportFilterForm.base_fields) | ({'format'} if export else set())
    if set(query) - allowed or any(len(query.getlist(key)) != 1 for key in query):
        raise AccountError('VALIDATION_ERROR', 'Unknown or repeated report filter.', 422)
    values = form_data(ReportFilterForm(query))
    if export and query.get('format') not in ('xlsx', 'csv'):
        raise AccountError('VALIDATION_ERROR', 'format must be xlsx or csv.', 422)
    return values
