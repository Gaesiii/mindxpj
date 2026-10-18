import hashlib
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase
from school_app.accounts.services import AccountError


class ModelAssetTests(SimpleTestCase):
    def setUp(self):
        from school_app.vision import model_assets
        self.assets = model_assets
        self.data = b'fixture-model-bytes'
        self.manifest = [{'filename': 'fixture.onnx', 'size': len(self.data),
                          'sha256': hashlib.sha256(self.data).hexdigest(),
                          'source': 'https://huggingface.co/opencv/fixture'}]
        self.patch = patch.object(model_assets, 'MODELS', self.manifest)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_runtime_requires_prepared_model_and_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen') as network:
            with self.assertRaises(AccountError) as error:
                self.assets.ensure_models(directory)
            self.assertEqual(error.exception.code, 'VISION_UNAVAILABLE')
            network.assert_not_called()

    def test_valid_prepared_model_returns_path_without_network(self):
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen') as network:
            target = Path(directory) / 'fixture.onnx'
            target.write_bytes(self.data)
            self.assertEqual(self.assets.ensure_models(directory), [target])
            network.assert_not_called()

    def test_runtime_rejects_same_size_corrupted_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'fixture.onnx').write_bytes(b'x' * len(self.data))
            with self.assertRaises(AccountError):
                self.assets.ensure_models(directory)

    def test_build_downloads_atomically_and_verifies_digest(self):
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen', return_value=io.BytesIO(self.data)):
            target = self.assets.ensure_models(directory, download=True)[0]
            self.assertEqual(target.read_bytes(), self.data)
            self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_failed_download_preserves_existing_file_and_removes_staging(self):
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen', return_value=io.BytesIO(b'x' * len(self.data))):
            target = Path(directory) / 'fixture.onnx'
            target.write_bytes(b'previous file')
            with self.assertRaises(AccountError):
                self.assets.ensure_models(directory, download=True)
            self.assertEqual(target.read_bytes(), b'previous file')
            self.assertEqual(list(Path(directory).iterdir()), [target])
