"""
URL configuration for core app (web views).
"""
from django.urls import path

# #region agent log
import json
try:
    with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"apps/core/urls.py:7","message":"Starting core.urls import","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
except: pass
# #endregion

try:
    # #region agent log
    try:
        with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"apps/core/urls.py:13","message":"Attempting to import views","data":{},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion
    
    from .views import home, login_view, dashboard, settings_view
    
    # #region agent log
    try:
        with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"apps/core/urls.py:19","message":"Views imported successfully","data":{"home":callable(home),"login_view":callable(login_view)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"apps/core/urls.py:25","message":"ERROR importing views","data":{"error":str(e),"type":type(e).__name__},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion
    raise

app_name = 'core'

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('settings/', settings_view, name='settings'),
]

# #region agent log
try:
    with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"apps/core/urls.py:37","message":"core urlpatterns created","data":{"count":len(urlpatterns)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
except: pass
# #endregion

