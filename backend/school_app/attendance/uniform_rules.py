from school_app.core.enums import ObservedUniform, UniformStatus
from .forms import strict_fields, text, invalid


def validate_uniform(payload, required):
    strict_fields(payload, ['observed_uniform','uniform_status','reason','note'], ['observed_uniform','uniform_status'])
    observed, status = payload['observed_uniform'], payload['uniform_status']
    if not isinstance(observed, str) or observed not in ObservedUniform.values:
        invalid('Select an observed uniform.')
    if not isinstance(status, str) or status not in [UniformStatus.COMPLIANT, UniformStatus.NON_COMPLIANT]:
        invalid('Select COMPLIANT or NON_COMPLIANT.')
    reason = text(payload, 'reason', required=status == UniformStatus.NON_COMPLIANT)
    note = text(payload, 'note', required=observed == ObservedUniform.OTHER)
    if status == UniformStatus.COMPLIANT and observed != required:
        invalid('COMPLIANT must match the session uniform snapshot.')
    return {'observed_uniform': observed, 'uniform_status': status, 'uniform_reason': reason, 'uniform_note': note}
