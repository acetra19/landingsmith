"""
Startup wrapper with diagnostics for Railway.
Prints environment info before launching uvicorn so we can debug
deployment failures from Railway logs.
"""

import os
import sys
import traceback

print("=" * 50)
print("LandingSmith Startup Diagnostics")
print("=" * 50)
print(f"Python:    {sys.version}")
print(f"CWD:       {os.getcwd()}")
print(f"PORT:      {os.environ.get('PORT', 'NOT SET')}")
print(f"DB_URL:    {os.environ.get('WEBREACH_DATABASE_URL', 'NOT SET')[:30]}...")
print(f"DATABASE_URL present: {'DATABASE_URL' in os.environ}")

railway_vars = {k: v[:20] for k, v in os.environ.items() if k.startswith("RAILWAY_")}
print(f"RAILWAY_* vars: {list(railway_vars.keys())}")

errors = []

try:
    import fastapi
    print(f"FastAPI:   {fastapi.__version__} OK")
except Exception as e:
    errors.append(f"FastAPI import: {e}")

try:
    import uvicorn
    print(f"Uvicorn:   {uvicorn.__version__} OK")
except Exception as e:
    errors.append(f"Uvicorn import: {e}")

try:
    from config.settings import settings
    print(f"Settings:  loaded OK (db_url={settings.db_url[:30]}...)")
except Exception as e:
    print(f"Settings:  FAILED - {e}")
    traceback.print_exc()
    errors.append(f"Settings: {e}")

try:
    from dashboard.app import app
    print("App:       imported OK")
except Exception as e:
    print(f"App:       FAILED - {e}")
    traceback.print_exc()
    errors.append(f"App import: {e}")

if errors:
    print("\n!!! ERRORS DETECTED !!!")
    for err in errors:
        print(f"  - {err}")
    print("Attempting to start anyway with minimal app...")

    if "app" not in dir():
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI()

        @app.get("/health")
        def health():
            return JSONResponse({"status": "degraded", "errors": errors})

print("=" * 50)

port = int(os.environ.get("PORT", 8000))
print(f"Starting uvicorn on 0.0.0.0:{port}")
sys.stdout.flush()

uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
