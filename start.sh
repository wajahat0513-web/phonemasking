#!/bin/bash
# Startup script for Railway deployment
# Reads PORT from environment variable, defaults to 8080 if not set

PORT=${PORT:-8080}
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"

