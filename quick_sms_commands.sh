# Quick Twilio Message Test Commands
# Replace YOUR_ACCOUNT_SID and YOUR_AUTH_TOKEN with your actual credentials

# METHOD 1: Send via Twilio Messages API (Direct SMS)
# This bypasses Proxy but is fastest for testing
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json" \
  -u "YOUR_ACCOUNT_SID:YOUR_AUTH_TOKEN" \
  --data-urlencode "From=+18046046355" \
  --data-urlencode "To=+13035550001" \
  --data-urlencode "Body=Quick test message"

# METHOD 2: Send via Proxy (Triggers /intercept)
# This is the proper way - sends through the session
curl -X POST "https://proxy.twilio.com/v1/Services/YOUR_PROXY_SERVICE_SID/Sessions/KC0ca3c89a59696b02eda0dc2b4144408d/Participants/PARTICIPANT_SID/MessageInteractions" \
  -u "YOUR_ACCOUNT_SID:YOUR_AUTH_TOKEN" \
  --data-urlencode "Body=Test message through proxy"

# PowerShell version (easier on Windows):
$accountSid = "YOUR_ACCOUNT_SID"
$authToken = "YOUR_AUTH_TOKEN"
$pair = "$($accountSid):$($authToken)"
$encodedCreds = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($pair))

Invoke-WebRequest -Uri "https://api.twilio.com/2010-04-01/Accounts/$accountSid/Messages.json" `
  -Method POST `
  -Headers @{Authorization = "Basic $encodedCreds"} `
  -Body @{
    From = "+18046046355"
    To = "+13035550001"
    Body = "Test message from PowerShell"
  }
