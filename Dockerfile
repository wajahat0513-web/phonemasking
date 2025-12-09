# Use Python 3.13 to match Railway's environment
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Run the application using uvicorn (matching Railway's start command)
# Uses PORT env var if set, otherwise defaults to 8080
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}

