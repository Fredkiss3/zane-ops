"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 5.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-^@$8fc&u2j)4@k+p+bg0ei8sm+@+pwq)hstk$a*0*7#k54kybx"
)

env = os.environ.get("ENVIRONMENT", "DEVELOPMENT")
PRODUCTION_ENV = "PRODUCTION"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = not env == PRODUCTION_ENV
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6381/0")

## We will only support one root domain on production
## And it will be in the format domain.com (without `http://` or `https://`)
root_domain = os.environ.get("ROOT_DOMAIN")
zane_app_domain = os.environ.get("ZANE_APP_DOMAIN")
ROOT_DOMAIN = "zane.local" if root_domain is None else root_domain
ZANE_APP_DOMAIN = ROOT_DOMAIN if zane_app_domain is None else zane_app_domain
ALLOWED_HOSTS = (
    ["zane.local", "localhost", "127.0.0.1"] if root_domain is None else [root_domain]
)

## This is necessary for making sure that CSRF protections work on production
CSRF_TRUSTED_ORIGINS = (
    ["http://zane.local", "https://zane.local"]
    if root_domain is None
    else [f"https://{root_domain}"]
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "zane_api.apps.ZaneApiConfig",
    "rest_framework",
    "drf_spectacular",
    "django_celery_results",
    "django_celery_beat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "zane"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "password"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5434"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DB Logging for queries

LOGGING = {
    "version": 1,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "django.db.backends": {
            "level": "DEBUG",
            "handlers": ["console"],
        }
    },
}

# Django Rest framework

REST_FRAMEWORK_DEFAULT_RENDERER_CLASSES = ("rest_framework.renderers.JSONRenderer",)

if DEBUG:
    REST_FRAMEWORK_DEFAULT_RENDERER_CLASSES = (
        REST_FRAMEWORK_DEFAULT_RENDERER_CLASSES
        + ("rest_framework.renderers.BrowsableAPIRenderer",)
    )

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": REST_FRAMEWORK_DEFAULT_RENDERER_CLASSES,
    "EXCEPTION_HANDLER": "zane_api.views.auth.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# DRF SPECTACULAR, for OpenAPI schema generation

SPECTACULAR_SETTINGS = {
    "TITLE": "ZaneOps API",
    "DESCRIPTION": "Your deployment, simplified. Everything handled for you.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# For having colorized output in tests
TEST_RUNNER = "redgreenunittest.django.runner.RedGreenDiscoverRunner"

# Celery config
CELERY_BROKER_URL = REDIS_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Zane proxy config
CADDY_PROXY_ADMIN_HOST = os.environ.get(
    "CADDY_PROXY_ADMIN_HOST", "http://localhost:2019"
)
CADDY_PROXY_SERVICE = "zane_zane-proxy"
