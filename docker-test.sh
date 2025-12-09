#!/bin/bash
# Script to test the Docker container locally

echo "Building Docker image..."
docker build -t phonemasking:test .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

echo ""
echo "✅ Docker image built successfully!"
echo ""
echo "To run the container, use:"
echo "  docker run -p 8080:8080 --env-file .env phonemasking:test"
echo ""
echo "Or with individual environment variables:"
echo "  docker run -p 8080:8080 \\"
echo "    -e TWILIO_ACCOUNT_SID=your_sid \\"
echo "    -e TWILIO_AUTH_TOKEN=your_token \\"
echo "    -e TWILIO_PROXY_SERVICE_SID=your_proxy_sid \\"
echo "    -e TWILIO_MESSAGING_SERVICE_SID=your_messaging_sid \\"
echo "    -e AIRTABLE_BASE_ID=your_base_id \\"
echo "    -e AIRTABLE_API_KEY=your_api_key \\"
echo "    phonemasking:test"


