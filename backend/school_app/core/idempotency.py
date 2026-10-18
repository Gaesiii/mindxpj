"""Atomic actor/action scoped retries. Caller MUST recheck scope before this helper."""
import hashlib
import json
from datetime import timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone
from school_app.accounts.services import AccountError
from .models import IdempotencyRequest, ChangeLog


def run_idempotent(user, operation, key, payload, callback):
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise AccountError('VALIDATION_ERROR', 'Idempotency-Key must contain 1 to 128 characters.', 422)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    with transaction.atomic():
        now = timezone.now()
        existing = IdempotencyRequest.objects.filter(actor=user, operation=operation, key=key).first()
        if existing and existing.expires_at > now:
            if existing.payload_hash != digest:
                raise AccountError('IDEMPOTENCY_CONFLICT', 'Key already used with a different payload.', 409)
            return existing.response_json, existing.response_status
        if existing:
            existing.delete()
        # Claim the unique key before reading mutable workflow state. This
        # also acquires SQLite's write lock; deferred reads alone do not.
        try:
            with transaction.atomic():
                claim = IdempotencyRequest.objects.create(actor=user, operation=operation, key=key, payload_hash=digest, response_json={}, expires_at=now+timedelta(hours=24))
        except IntegrityError as exc:
            if 'unique' not in str(exc).lower():
                raise
            raise AccountError('DATABASE_BUSY', 'Concurrent retry; retry the same key.', 409) from None
        body, status = callback()
        claim.response_json, claim.response_status = body, status
        claim.save(update_fields=['response_json','response_status'])
        return body, status


def record_change(user, entity, action, before, after, reason=None):
    ChangeLog.objects.create(actor=user, entity_type=entity.__class__.__name__, entity_id=entity.pk, action=action, before=before, after=after, reason=reason)


def check_version(entity, expected):
    if type(expected) is not int or expected < 0:
        raise AccountError('VALIDATION_ERROR', 'A nonnegative integer version is required.', 422)
    if entity.version != expected:
        raise AccountError('VERSION_CONFLICT', 'Record changed; reload it.', 409, {'expected_version': expected, 'current_version': entity.version})
