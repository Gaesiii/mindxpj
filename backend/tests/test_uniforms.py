from django.test import SimpleTestCase
from school_app.attendance import uniform_rules
from school_app.accounts.services import AccountError


class UniformRulesTests(SimpleTestCase):
    def test_matching_uniform_is_compliant(self):
        self.assertTrue(hasattr(uniform_rules, 'validate_uniform'))
        self.assertEqual(uniform_rules.validate_uniform({'observed_uniform':'SHIRT','uniform_status':'COMPLIANT'}, 'SHIRT')['uniform_status'], 'COMPLIANT')

    def test_mismatch_compliant_rejected(self):
        self.assertTrue(hasattr(uniform_rules, 'validate_uniform'))
        with self.assertRaises(AccountError):
            uniform_rules.validate_uniform({'observed_uniform':'SPORTS','uniform_status':'COMPLIANT'}, 'SHIRT')

    def test_noncompliant_and_other_require_explanations(self):
        self.assertTrue(hasattr(uniform_rules, 'validate_uniform'))
        for payload in [{'observed_uniform':'SPORTS','uniform_status':'NON_COMPLIANT'}, {'observed_uniform':'OTHER','uniform_status':'NON_COMPLIANT','reason':'wrong'}]:
            with self.assertRaises(AccountError):
                uniform_rules.validate_uniform(payload, 'SHIRT')
