# PowerShell script to test the Docker container locally

Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build -t phonemasking:test .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Docker image built successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To run the container, use:" -ForegroundColor Yellow
Write-Host "  docker run -p 8080:8080 --env-file .env phonemasking:test"
Write-Host ""
Write-Host "Or with individual environment variables:" -ForegroundColor Yellow
Write-Host "  docker run -p 8080:8080 \"
Write-Host "    -e TWILIO_ACCOUNT_SID=your_sid \"
Write-Host "    -e TWILIO_AUTH_TOKEN=your_token \"
Write-Host "    -e TWILIO_PROXY_SERVICE_SID=your_proxy_sid \"
Write-Host "    -e TWILIO_MESSAGING_SERVICE_SID=your_messaging_sid \"
Write-Host "    -e AIRTABLE_BASE_ID=your_base_id \"
Write-Host "    -e AIRTABLE_API_KEY=your_api_key \"
Write-Host "    phonemasking:test"


