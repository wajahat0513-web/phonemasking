from fastapi import FastAPI
from config import settings
from routers import sessions, intercept, numbers
from utils.logger import log_info

app = FastAPI(title="Phone Masking Service")

# Register Routers
app.include_router(sessions.router)
app.include_router(intercept.router)
app.include_router(numbers.router)

@app.on_event("startup")
async def startup_event():
    log_info("Starting Phone Masking Service")
    log_info(f"Loaded configuration for environment: {settings.AIRTABLE_BASE_ID}")
    
    # Start delivery fallback worker
    from services.fallback_worker import start_fallback_worker
    start_fallback_worker()

@app.get("/")
async def root():
    return {"message": "Phone Masking Service is running"}

@app.get("/debug/sitters")
async def debug_sitters():
    from services.airtable_client import sitters_table
    try:
        records = sitters_table.all(max_records=10)
        return [{"id": r["id"], "fields": r["fields"]} for r in records]
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
