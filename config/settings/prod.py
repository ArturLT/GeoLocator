from .base import *
from decouple import config

DEBUG = False

ALLOWED_HOSTS = config.list('ALLOWED_HOSTS', default=[])

DATABASES = {
    'default': config.db_url()
}