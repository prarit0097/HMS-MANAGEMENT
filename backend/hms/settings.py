"""Local foundation settings. Production requires explicit private PostgreSQL credentials."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = os.getenv('HMS_ENV', 'development')
if ENVIRONMENT not in {'development', 'staging', 'production'}:
    raise ImproperlyConfigured('HMS_ENV must be development, staging or production.')
DEBUG = ENVIRONMENT == 'development'
SECRET_KEY = os.getenv('HMS_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('HMS_SECRET_KEY is required outside development.')
    # Ephemeral: never a committed credential; local sessions expire on restart.
    from django.core.management.utils import get_random_secret_key
    SECRET_KEY = get_random_secret_key()
ALLOWED_HOSTS = os.getenv('HMS_ALLOWED_HOSTS', '127.0.0.1,localhost,testserver' if DEBUG else '').split(',')
ROOT_URLCONF = 'hms.urls'
WSGI_APPLICATION = 'hms.wsgi.application'
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'rest_framework', 'apps.core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'apps.core.middleware.NetworkPolicyMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
DB_ENGINE = os.getenv('HMS_DB_ENGINE', 'sqlite' if DEBUG else 'postgresql')
if DB_ENGINE == 'sqlite' and DEBUG:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
else:
    if DB_ENGINE != 'postgresql':
        raise ImproperlyConfigured('PostgreSQL is mandatory outside development.')
    for key in ('HMS_DB_NAME', 'HMS_DB_USER', 'HMS_DB_PASSWORD', 'HMS_DB_HOST', 'HMS_ALLOWED_HOSTS'):
        if not os.getenv(key):
            raise ImproperlyConfigured(f'{key} is required outside development.')
    sslmode = os.getenv('HMS_DB_SSLMODE', 'disable' if DEBUG else 'require')
    if not DEBUG and sslmode not in {'require', 'verify-ca', 'verify-full'}:
        raise ImproperlyConfigured('PostgreSQL TLS is mandatory outside development.')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.environ['HMS_DB_NAME'], 'USER': os.environ['HMS_DB_USER'], 'PASSWORD': os.environ['HMS_DB_PASSWORD'], 'HOST': os.environ['HMS_DB_HOST'], 'PORT': os.getenv('HMS_DB_PORT', '5432'), 'OPTIONS': {'sslmode': sslmode}}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'Asia/Kolkata'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
X_FRAME_OPTIONS = 'DENY'
CSRF_TRUSTED_ORIGINS = os.getenv('HMS_CSRF_TRUSTED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173' if DEBUG else '').split(',')
CSRF_FAILURE_VIEW = 'apps.core.middleware.csrf_failure'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'], 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'], 'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'], 'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.BoundedPagination', 'PAGE_SIZE': 25, 'EXCEPTION_HANDLER': 'apps.core.api.safe_exception_handler'}
HMS_TRUSTED_PROXIES = tuple(filter(None, os.getenv('HMS_TRUSTED_PROXIES', '').split(',')))
HMS_IP_ALLOWLIST = list(filter(None, os.getenv('HMS_IP_ALLOWLIST', '').split(',')))
HMS_IP_BLOCKLIST = list(filter(None, os.getenv('HMS_IP_BLOCKLIST', '').split(',')))
def env_boolean(name, default='0'):
    value = os.getenv(name, default).lower().strip()
    if value not in {'0', '1', 'true', 'false'}:
        raise ImproperlyConfigured(f'{name} must be true, false, 1 or 0.')
    return value in {'1', 'true'}
HMS_IP_ALLOWLIST_ONLY = env_boolean('HMS_IP_ALLOWLIST_ONLY')
