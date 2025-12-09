#!/usr/bin/env python3
"""
Startup script for Railway deployment.
Reads PORT from environment variable, defaults to 8080 if not set.
"""
import os
import sys

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Import uvicorn and run the app
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port)

