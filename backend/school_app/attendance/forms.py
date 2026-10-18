"""Strict JSON schema helpers shared with QR confirmation."""
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from school_app.accounts.services import AccountError


def invalid(message):
    raise AccountError('VALIDATION_ERROR', message, 422)


def strict_fields(payload, allowed, required=()):
    if not isinstance(payload, dict) or set(payload)-set(allowed) or set(required)-set(payload):
        invalid('Missing or unsupported fields.')


def integer(payload, name):
    value = payload.get(name)
    if type(value) is not int or value < 0:
        invalid(name+' must be a nonnegative integer.')
    return value


def text(payload, name, required=False):
    value = payload.get(name)
    if value is None:
        if required:
            invalid(name+' is required.')
        return None
    if not isinstance(value, str) or len(value) > 1000:
        invalid(name+' must be a string of at most 1000 characters.')
    value = value.strip() or None
    if required and value is None:
        invalid(name+' is required.')
    return value


def arrival(value):
    if not isinstance(value, str):
        invalid('arrived_at must be a datetime string with timezone.')
    try:
        parsed = parse_datetime(value)
    except ValueError:
        parsed = None
    if parsed is None or timezone.is_naive(parsed):
        invalid('arrived_at must include a timezone offset.')
    return parsed
