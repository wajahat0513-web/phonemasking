#!/bin/sh
# Wrapper script for Railway that properly handles PORT environment variable
# This script ensures PORT is always an integer before passing to uvicorn

PORT=${PORT:-8080}
exec python start.py
