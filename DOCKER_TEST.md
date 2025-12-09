# Docker Local Testing Guide

This guide helps you test the application locally using Docker to validate it will run correctly on Railway.

## Prerequisites

1. **Install Docker Desktop** (if not already installed):
   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop
   - Verify installation: `docker --version`

## Building the Docker Image

### On Windows (PowerShell):
```powershell
docker build -t phonemasking:test .
```

### On Linux/Mac:
```bash
docker build -t phonemasking:test .
```

## Running the Container

### Option 1: Using .env file (Recommended)
Make sure you have a `.env` file with all required environment variables:
```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PROXY_SERVICE_SID=your_proxy_service_sid
TWILIO_MESSAGING_SERVICE_SID=your_messaging_service_sid
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_API_KEY=your_api_key
```

Then run:
```powershell
docker run -p 8080:8080 --env-file .env phonemasking:test
```

### Option 2: Using individual environment variables
```powershell
docker run -p 8080:8080 `
  -e TWILIO_ACCOUNT_SID=your_sid `
  -e TWILIO_AUTH_TOKEN=your_token `
  -e TWILIO_PROXY_SERVICE_SID=your_proxy_sid `
  -e TWILIO_MESSAGING_SERVICE_SID=your_messaging_sid `
  -e AIRTABLE_BASE_ID=your_base_id `
  -e AIRTABLE_API_KEY=your_api_key `
  phonemasking:test
```

## Testing the Application

Once the container is running:

1. **Check if the service is running:**
   ```powershell
   curl http://localhost:8080/
   ```
   Or open in browser: http://localhost:8080/

2. **Check the API docs:**
   - Open: http://localhost:8080/docs

3. **Check container logs:**
   ```powershell
   docker logs <container_id>
   ```

## Validating Railway Compatibility

The Dockerfile is configured to match Railway's deployment:
- ✅ Python 3.13 (matches Railway's Python version)
- ✅ Port 8080 (Railway sets PORT env var, defaulting to 8080)
- ✅ Uvicorn command matches Railway's start command
- ✅ Working directory structure matches Railway

## Troubleshooting

### Container won't start
- Check logs: `docker logs <container_id>`
- Verify all environment variables are set correctly
- Ensure port 8080 is not already in use

### Import errors
- Verify all files are copied correctly
- Check that `config.py` and other modules are in the container

### Airtable connection errors
- Verify AIRTABLE_API_KEY and AIRTABLE_BASE_ID are correct
- Check that the field names match (should be "Event" not "Event Type")

## Cleanup

Stop and remove the container:
```powershell
docker stop <container_id>
docker rm <container_id>
```

Remove the image:
```powershell
docker rmi phonemasking:test
```


