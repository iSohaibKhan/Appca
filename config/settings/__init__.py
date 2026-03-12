"""
Django settings for Appca project.

This module imports the appropriate settings based on the environment.
"""
import os

env = os.environ.get('DJANGO_ENV', 'local')

if env == 'production':
    from .production import *  # noqa
else:
    from .local import *  # noqa

