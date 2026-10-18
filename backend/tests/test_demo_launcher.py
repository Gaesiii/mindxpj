from pathlib import Path
import subprocess
import sys
import tempfile
from django.test import SimpleTestCase


class ResumeDemoTests(SimpleTestCase):
    def test_resume_refuses_missing_database_before_seeding(self):
        script = Path(__file__).resolve().parents[2] / '.document-tools/run_demo.py'
        with tempfile.TemporaryDirectory(prefix='projectmindx-demo-ui-') as directory:
            result = subprocess.run([sys.executable, str(script), '--resume-runtime', directory],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('existing demo.sqlite3 and demo-login.txt', result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_resume_refuses_non_demo_directory(self):
        script = Path(__file__).resolve().parents[2] / '.document-tools/run_demo.py'
        with tempfile.TemporaryDirectory(prefix='unrelated-data-') as directory:
            result = subprocess.run([sys.executable, str(script), '--resume-runtime', directory],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('direct temporary demo directory', result.stderr)
