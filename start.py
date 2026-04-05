"""
Startup wrapper with diagnostics for Railway.
Prints environment info, then launches uvicorn.
If the main app fails to import, starts a minimal fallback server.
"""

import os
import sys
import traceback

print("=" * 50, flush=True)
print("LandingSmith Startup Diagnostics", flush=True)
print("=" * 50, flush=True)
print(f"Python:    {sys.version}", flush=True)
print(f"CWD:       {os.getcwd()}", flush=True)
print(f"sys.path:  {sys.path[:3]}", flush=True)
print(f"PORT:      {os.environ.get('PORT', 'NOT SET')}", flush=True)
print(f"DB env:    WEBREACH={os.environ.get('WEBREACH_DATABASE_URL', 'unset')[:25]}", flush=True)
print(f"           DATABASE_URL present: {'DATABASE_URL' in os.environ}", flush=True)

ls_app = os.listdir(".")
print(f"Files in /app: {ls_app[:15]}", flush=True)

if os.path.isdir("dashboard"):
    print(f"dashboard/:  {os.listdir('dashboard')}", flush=True)
else:
    print("WARNING: dashboard/ directory not found!", flush=True)

import uvicorn

app = None
errors = []

try:
    from dashboard.app import app as main_app
    app = main_app
    print("App imported OK", flush=True)
except Exception as e:
    msg = f"App import failed: {e}"
    print(msg, flush=True)
    traceback.print_exc()
    errors.append(msg)

if app is None:
    print("Using fallback minimal app", flush=True)
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.get("/health")
    def health():
        return JSONResponse({"status": "degraded", "errors": errors})

    @app.get("/")
    def root():
        return JSONResponse({"status": "degraded", "message": "Main app failed to load", "errors": errors})

port = int(os.environ.get("PORT", 8000))
print(f"Starting uvicorn on 0.0.0.0:{port}", flush=True)
sys.stdout.flush()
sys.stderr.flush()

uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
