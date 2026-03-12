"""
WSGI config for Appca project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""
import os
import json

# #region agent log
try:
    with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"config/wsgi.py:12","message":"WSGI application loading","data":{"settings_module":os.environ.get('DJANGO_SETTINGS_MODULE')},"timestamp":int(__import__('time').time()*1000)}) + '\n')
except: pass
# #endregion

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

# #region agent log
try:
    with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"config/wsgi.py:20","message":"Getting WSGI application","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
except: pass
# #endregion

application = get_wsgi_application()

# #region agent log
try:
    from django.conf import settings
    from django.urls import get_resolver
    resolver = get_resolver()
    try:
        with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"config/wsgi.py:28","message":"WSGI app created, checking resolver","data":{"url_pattern_count":len(resolver.url_patterns),"root_urlconf":settings.ROOT_URLCONF},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
except: pass
# #endregion

