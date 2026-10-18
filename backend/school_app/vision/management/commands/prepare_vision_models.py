from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from school_app.accounts.services import AccountError
from school_app.vision.model_assets import ensure_models


class Command(BaseCommand):
    help = 'Download pinned YuNet/SFace weights and verify SHA-256 (setup/build only).'

    def handle(self, *args, **options):
        try:
            paths = ensure_models(settings.VISION_MODEL_DIR, download=True)
        except AccountError as error:
            raise CommandError(error.message) from error
        self.stdout.write(f'Prepared {len(paths)} verified local face models.')
