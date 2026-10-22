"""Local MVP foundation. Environment variables are documented in backend/README.md."""
import os
import hashlib
import tempfile
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY before running Django; see backend/README.md.")
VERCEL_DEMO = os.environ.get('VERCEL') == '1'
DEBUG = os.environ.get("DJANGO_DEBUG", "false" if VERCEL_DEMO else "true").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]"
).split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "school_app.core.apps.CoreConfig",
    "school_app.accounts.apps.AccountsConfig",
    "school_app.academics",
    "school_app.students",
    "school_app.schedules",
    "school_app.attendance",
    "school_app.qr",
    "school_app.vision",
    "school_app.reports",
    "school_app.management_app",
    "school_app.demo_ui",
]
MIDDLEWARE = [
    "school_app.core.middleware.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME":
    os.environ.get("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3"))}}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
APPEND_SLASH = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_FAILURE_VIEW = "school_app.core.errors.csrf_failure"
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"
# No public media route, templates, static assets or Django Admin in A01.

# QR history stays available to reports; its old write/scan API is retired by default.
QR_ENABLED = os.environ.get('QR_ENABLED', 'false').lower() == 'true'
VISION_MODEL_DIR = BASE_DIR / 'vision_models'
VISION_FACE_MIN_COSINE = float(os.environ.get('VISION_FACE_MIN_COSINE', '0.45'))
VISION_FACE_MIN_COSINE_MARGIN = float(os.environ.get('VISION_FACE_MIN_COSINE_MARGIN', '0.10'))
if not 0 <= VISION_FACE_MIN_COSINE <= 1 or not 0 <= VISION_FACE_MIN_COSINE_MARGIN <= 2:
    raise ImproperlyConfigured('Face cosine threshold/margin is outside its valid range.')
VISION_MIN_SHARPNESS = float(os.environ.get('VISION_MIN_SHARPNESS', '50'))
VISION_ANALYSES_PER_MINUTE = 20
VISION_AUTO_MIN_COSINE = float(os.environ.get('VISION_AUTO_MIN_COSINE', '0.60'))
VISION_AUTO_MIN_MARGIN = float(os.environ.get('VISION_AUTO_MIN_MARGIN', '0.15'))
if not 0 <= VISION_AUTO_MIN_COSINE <= 1 or not 0 <= VISION_AUTO_MIN_MARGIN <= 2:
    raise ImproperlyConfigured('Automatic face thresholds are outside their valid range.')
VISION_ENROLLMENT_TOTAL_BYTES = int(os.environ.get(
    'VISION_ENROLLMENT_TOTAL_BYTES', str((3 if VERCEL_DEMO else 15) * 1024 * 1024)))
if VISION_ENROLLMENT_TOTAL_BYTES <= 0:
    raise ImproperlyConfigured('VISION_ENROLLMENT_TOTAL_BYTES must be positive.')
# Demo colors only. Customize to the school's actual clothes, then evaluate.
import json
VISION_UNIFORM_HSV = json.loads(os.environ.get('VISION_UNIFORM_HSV',
    '{"SHIRT":[[0,0,160],[179,70,255]],"SPORTS":[[95,80,50],[135,255,255]]}'))
DATA_UPLOAD_MAX_NUMBER_FILES = 10

# Local UI authorized on 18/10/2026; PM API acceptance is a separate decision.
TEMPLATES = [{
    'BACKEND':'django.template.backends.django.DjangoTemplates',
    'DIRS':[], 'APP_DIRS':True,
    'OPTIONS':{'context_processors':['django.template.context_processors.request']},
}]
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
UNIFORM_DEMO_ROOT = os.environ.get('UNIFORM_DEMO_ROOT','')

if VERCEL_DEMO:
    platform_hosts = [os.environ.get(name, '').strip() for name in
                      ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL')]
    ALLOWED_HOSTS = list(dict.fromkeys(host for host in [
        *os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(','), *platform_hosts
    ] if host.strip()))
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS]
    deployment = os.environ.get('VERCEL_URL') or os.environ.get('VERCEL_PROJECT_PRODUCTION_URL') or 'local-build'
    runtime_root = Path(tempfile.gettempdir()) / ('mindx-demo-' + hashlib.sha256(deployment.encode()).hexdigest()[:16])
    DATABASES['default']['NAME'] = os.environ.get('DJANGO_DB_PATH', str(runtime_root / 'db.sqlite3'))
    DATABASES['default']['OPTIONS'] = {'timeout': 20}
    PRIVATE_MEDIA_ROOT = runtime_root / 'private_media'
    FILE_UPLOAD_TEMP_DIR = str(runtime_root / 'uploads')
    VERCEL_DEMO_TEMPLATE = BASE_DIR / '.vercel-demo' / 'template.sqlite3'
    SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
    SESSION_COOKIE_AGE = 60 * 60
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    MIDDLEWARE.insert(0, 'config.vercel_demo.DemoBootstrapMiddleware')
