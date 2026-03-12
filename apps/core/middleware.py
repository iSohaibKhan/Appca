"""
Debug middleware to log URL resolution.
"""
import json

class URLDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # #region agent log
        try:
            with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"apps/core/middleware.py:12","message":"Request received","data":{"path":request.path,"method":request.method},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        # #region agent log
        try:
            from django.urls import get_resolver
            resolver = get_resolver()
            try:
                match = resolver.resolve(request.path)
                try:
                    with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"apps/core/middleware.py:20","message":"URL resolved","data":{"path":request.path,"view":str(match.func),"url_name":match.url_name},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
            except Exception as e:
                try:
                    with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"apps/core/middleware.py:25","message":"URL resolution failed","data":{"path":request.path,"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
        except Exception as e:
            try:
                with open(r'c:\Users\HAROON TRADERS\Desktop\appca\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"apps/core/middleware.py:30","message":"ERROR in resolver check","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
        # #endregion
        
        response = self.get_response(request)
        return response


