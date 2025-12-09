# Use Python 3.13 to match Railway's environment
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies in a single layer
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only necessary application files (excludes files in .dockerignore)
COPY . .

# Make startup script executable
RUN chmod +x start.sh

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Run the application using the startup script
# The script handles PORT env var properly
CMD ./start.sh

